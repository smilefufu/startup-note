from datetime import datetime
import json
import re
import hashlib
import base64
import time 
from flask import render_template, request, Response, redirect
from run import app
from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid
from wxcloudrun.model import Counters, DifyUsers
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response
from wxcloudrun import db
import requests

EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

def is_valid_email(email):
    return re.match(EMAIL_REGEX, email) is not None

def jsonify(data):
    # 使用自定义的 JSON 响应函数，并确保 ensure_ascii=False
    return Response(json.dumps(data, ensure_ascii=False), content_type="application/json; charset=utf-8")


def reply_text(from_user, to_user, reply_txt):
    payload = {
        "ToUserName": to_user,
        "FromUserName": from_user,
        "CreateTime": int(datetime.now().strftime('%s')),
        "MsgType": 'text',
        "Content": reply_txt
    }
    return jsonify(payload)



@app.route('/')
def index():
    """
    :return: 返回index页面
    """
    return render_template('index.html')


@app.route('/api/count', methods=['POST'])
def count():
    """
    :return:计数结果/清除结果
    """

    # 获取请求体参数
    params = request.get_json()

    # 检查action参数
    if 'action' not in params:
        return make_err_response('缺少action参数')

    # 按照不同的action的值，进行不同的操作
    action = params['action']

    # 执行自增操作
    if action == 'inc':
        counter = query_counterbyid(1)
        if counter is None:
            counter = Counters()
            counter.id = 1
            counter.count = 1
            counter.created_at = datetime.now()
            counter.updated_at = datetime.now()
            insert_counter(counter)
        else:
            counter.id = 1
            counter.count += 1
            counter.updated_at = datetime.now()
            update_counterbyid(counter)
        return make_succ_response(counter.count)

    # 执行清0操作
    elif action == 'clear':
        delete_counterbyid(1)
        return make_succ_empty_response()

    # action参数错误
    else:
        return make_err_response('action参数错误')


@app.route('/api/count', methods=['GET'])
def get_count():
    """
    :return: 计数的值
    """
    counter = Counters.query.filter(Counters.id == 1).first()
    return make_succ_response(0) if counter is None else make_succ_response(counter.count)

@app.route('/api/gzh_msg', methods=['POST'])
def gzh_msg():
    headers = request.headers
    data = request.json
    if "action" in data and data["action"] == "CheckContainerPath":
        return make_succ_response(0)
    app.logger.info("http headers: %s", headers)
    app.logger.info("get data: %s", data)
    
    from_user = data['FromUserName']
    me = data['ToUserName']
    create_time = data['CreateTime']
    msg_type = data['MsgType']
    if msg_type == 'event' and data['Event'] == 'unsubscribe':
        # 过滤取消关注事件
        return make_succ_empty_response()
    if msg_type == 'text':
        try:
            content = data['Content']
        except KeyError:
            app.logger.info("get Content error: %s", data)
        if content.isdigit() and 4 <= len(content) <= 6:
            # 4-6 位数字，为发送的验证码
            app.logger.info(f"get register code:{content}")
            register_code = content
            user = DifyUsers.query.filter_by(register_code=register_code).first()
            if user and user.wx_openid:
                # 当前用户已经绑定过微信了
                return reply_text(me, from_user, f"已签到，无需重新发送")
            elif user:
                # 存在已知的注册验证码,未绑定微信
                user.wx_openid = from_user
                user.wx_unionid = headers.get("X-WX-UNIONID")
                user.wx_ip = headers.get("X-Original-Forwarded-For")
                user.wx_source = headers.get("X-WX-SOURCE")
                db.session.commit()
                return reply_text(me, from_user, f"签到成功！请返回网页填写登录邮箱。")
            else:
                #  系统没有分发过这个验证码
                return reply_text(me, from_user, f"这不是有效的签到码哟～")
        elif content.startswith('注册'):
            content = content.replace("：", ":")
            sp = content.split(":")
            app.logger.info("get content: %s", str(sp))
            if len(sp) == 2:
                email = sp[-1].strip()
                if is_valid_email(email=email):
                    # 注册用户-正式环境
                    invite_result = requests.get("https://dify.vongcloud.com/xinshu/api/invite",params={"email":email})
                    # 注册用户 - 测试环境
                    # invite_result = requests.get("http://localhost:5001/xinshu/api/invite",params={"email":email})
                    if invite_result.ok:
                        invite_json = invite_result.json()
                        if invite_json["result"] == "success":
                            invite_url = invite_json["invite-url"]
                            return reply_text(me, from_user, f"请在浏览器打开以下链接，完成注册：{invite_url}，您的注册邮箱是：{email}")
                        else:
                            invite_error = invite_json["error"]
                            return reply_text(me, from_user, f"遇到一点点小麻烦：{invite_error}")
                    else:
                        return reply_text(me, from_user, f"遇到一点点小麻烦,需要召唤管理员：{invite_result.text}")
                else:
                    return reply_text(me, from_user, f"邮箱格式有点点小问题，这样写-->  注册：zhangsan@example.com")
            return reply_text(me, from_user, f"格式有点点小问题，这样写：注册：zhangsan@example.com")
    elif msg_type == 'event':
        reply = "你好，感谢您的关注！"
        return reply_text(me, from_user, reply)
    return make_succ_response(0)

@app.route('/dify/landing/<version>', defaults={'version': 'v2'})
@app.route('/dify/landing')
def landing_page(version='v1'):
    app.logger.info("version: %s", version)
    user_name = request.args.get("user_name")
    user_name_b64 = base64.b64encode(user_name.encode('utf8')).decode('utf8')
    phone_num = request.args.get("phone_num")
    xiaoxi_uuid = request.args.get("xiaoxi_uuid")
    app.logger.info(f"落地页面跳转：{user_name},{phone_num}, {xiaoxi_uuid}")
    # 校验是否已有账号
    user = DifyUsers.query.filter_by(xx_xiaoxi_uuid=xiaoxi_uuid).first()
    if user:
        app.logger.info(f"用户 {user_name} 已经注册过了")
        if user.dify_email and user.dify_token:
            # 曾经注册过dify， 直接跳转
            return redirect("https://dify.vongcloud.com")    
        else:
            # 跳转过，但是未完成注册
            app.logger.info(f"用户 {user_name} 未完成注册")
            register_code = user.register_code
            if not register_code:
                # 未生成验证码
                register_code = generate_numeric_passcode(user_info={"user_name":user_name_b64, "phone_num":phone_num,"xiaoxi_uuid":xiaoxi_uuid})
                user.register_code = register_code
                db.session.commit()
    else:
        # 新用户，需要重新引导
        # 为用户生成一个随机验证码
        app.logger.info(f"用户 {user_name} 未注册过，需要引导注册")
        register_code = generate_numeric_passcode(user_info={"user_name":user_name_b64, "phone_num":phone_num,"xiaoxi_uuid":xiaoxi_uuid})
        # 构建一个新用户信息，包含注册随机码
        new_user = DifyUsers(
            xx_user_name = user_name_b64,
            xx_phone_num = phone_num,
            xx_xiaoxi_uuid = xiaoxi_uuid,
            register_code = register_code
        )
        db.session.add(new_user)
        db.session.commit()
    if version == 'v2':
        return render_template('landing_page_v2.html', user_name=user_name, phone_num=phone_num, xiaoxi_uuid=xiaoxi_uuid, register_code=register_code)
    else:
        return render_template('landing_page.html', user_name=user_name, phone_num=phone_num, xiaoxi_uuid=xiaoxi_uuid, register_code=register_code)

@app.route('/dify/verify_register_code')
def verify_register_code():
    register_code = request.args.get("register_code")
    xiaoxi_uuid = request.args.get("xiaoxi_uuid")
    # 校验是否已有账号, 是否包含了wx_openid
    user = DifyUsers.query.filter_by(xx_xiaoxi_uuid=xiaoxi_uuid).first()
    if user.wx_openid:
        # 已经从微信发送过签到码
        return make_succ_empty_response()
    else:
        # 微信侧还没有更新绑定签到码
        return make_err_response("")

@app.route('/dify/invite_email')
def invite_email():
    register_code = request.args.get("register_code")
    xiaoxi_uuid = request.args.get("xiaoxi_uuid")
    email = request.args.get("email")
    user = DifyUsers.query.filter_by(xx_xiaoxi_uuid=xiaoxi_uuid).first()
    if user:
        if is_valid_email(email=email):
            # 注册用户-正式环境
            invite_result = requests.get("https://dify.vongcloud.com/xinshu/api/invite",params={"email":email})
            # 注册用户 - 测试环境
            # invite_result = requests.get("http://host.docker.internal:5001/xinshu/api/invite",params={"email":email})
            if invite_result.ok:
                invite_json = invite_result.json()
                if invite_json["result"] == "success":
                    invite_url = invite_json["invite-url"]
                    user.dify_email = email
                    user.dify_token = invite_json["token"]
                    user.dify_invite_url = invite_url
                    db.session.commit()
                    return make_succ_response({"invite_url":invite_url})
                else:
                    invite_error = invite_json["error"]
                    # 邀请失败，用户可以自己处理
                    return make_err_response(f"遇到一点点小麻烦：{invite_error}")
            else:
                # 服务器故障，需要管理员
                return make_err_response(f"遇到一点点小麻烦,需要召唤管理员：{invite_result.text}")
        else:
            # 邮箱格式不对
            return make_err_response(f"邮箱格式有点点小问题，再检查一下")
    # 用户不存在，或者没有前面的步骤
    return make_err_response(f"遇到一点点小困难，刷新页面再试一下")


def generate_numeric_passcode(user_info:dict, length=6):
    """
    生成一个不易被推断的数字口令
    :param user_info: dict 包含用户相关信息 (如用户名, 手机号, UUID)
    :param length: 生成的数字口令长度 (默认为6, 可选4~6)
    :return: 生成的数字口令
    """
    if length < 4 or length > 6:
        raise ValueError("Passcode length must be between 4 and 6.")

    # 用户相关信息的组合（如用户名、手机号、UUID）
    user_identifier = "".join(user_info.values())
    
    # 附加信息：当前时间（精确到秒）
    current_time = str(int(time.time()))
    
    # 拼接用户标识和附加信息
    input_string = f"{user_identifier}{current_time}"
    
    # 使用 SHA-256 生成哈希值
    hashed = hashlib.sha256(input_string.encode('utf-8')).hexdigest()
    
    # 将哈希值转换为整数后取前 N 位
    numeric_passcode = str(int(hashed, 16))[:length]
    
    return numeric_passcode