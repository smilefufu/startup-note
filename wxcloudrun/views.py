from datetime import datetime
import json
import re
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
    data = request.json
    if "action" in data and data["action"] == "CheckContainerPath":
        return make_succ_response(0)
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
        if content.startswith('注册'):
            content = content.replace("：", ":")
            sp = content.split(":")
            app.logger.info("get content: %s", str(sp))
            if len(sp) == 2:
                email = sp[-1].strip()
                if is_valid_email(email=email):
                    # 注册用户
                    invite_result = requests.get("http://dify.vongcloud.com/xinshu/api/invite",params={"email":email})
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

@app.route('/dify/landing')
def landing_page():
    user_name = request.args.get("user_name")
    phone_num = request.args.get("phone_num")
    xiaoxi_uuid = request.args.get("xiaoxi_uuid")
    app.logger.info(f"落地页面跳转：{user_name},{phone_num}, {xiaoxi_uuid}")
    # 校验是否已有账号
    user = DifyUsers.query.filter_by(xx_xiaoxi_uuid=xiaoxi_uuid).first()
    if user:
        if user.dify_email and user.dify_token:
            # 曾经注册过dify， 直接跳转
            return redirect("https://dify.vongcloud.com")    
        else:
            # 跳转过，但是未完成注册
            pass
    else:
        # 新用户，需要重新引导
        new_user = DifyUsers(
            xx_user_name = user_name,
            xx_phone_num = phone_num,
            xx_xiaoxi_uuid = xiaoxi_uuid
        )
        db.session.add(new_user)
        db.session.commit()
    return render_template('landing_page.html')
    