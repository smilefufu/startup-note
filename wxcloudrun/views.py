from datetime import datetime
import json
from flask import render_template, request, Response
from run import app
from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid
from wxcloudrun.model import Counters
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response


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
                email = sp[-1]
                # TODO: 注册用户
                return reply_text(me, from_user, "注册功能还在开发中，敬请期待！")
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
    # TODO 校验是否关注了公众号
    
    # TODO 已关注公众号，跳转
    
    # TODO 未关注公众号，展示关注公众号
    return render_template('landing_page.html')
    
    # return make_succ_response(data={"user_name":user_name, "phone_num":phone_num, "xiaoxi_uuid":xiaoxi_uuid})