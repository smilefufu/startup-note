from datetime import datetime

from wxcloudrun import db


# 计数表
class Counters(db.Model):
    # 设置结构体表格名称
    __tablename__ = 'Counters'

    # 设定结构体对应表格的字段
    id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer, default=1)
    created_at = db.Column('createdAt', db.TIMESTAMP, nullable=False, default=datetime.now())
    updated_at = db.Column('updatedAt', db.TIMESTAMP, nullable=False, default=datetime.now())

# Dify用户表

class DifyUsers(db.Model):
    __tablename__ = 'DifyUsers'

    id = db.Column(db.Integer, primary_key=True)
    # XX_ 代表来自小栖平台的数据，包括用户名、手机号、uuid
    xx_user_name =  db.Column(db.String(100), nullable=False)
    xx_phone_num = db.Column(db.String(100), nullable=False)
    xx_xiaoxi_uuid = db.Column(db.String(100), nullable=False)
    # wx_  代表来自微信平台等数据
    wx_openid = db.Column(db.String(100), nullable=True)
    wx_unionid = db.Column(db.String(100), nullable=True)
    wx_ip = db.Column(db.String(100), nullable=True)
    wx_source = db.Column(db.String(100), nullable=True)
    # dify_ 代表来自dify平台的数据，包括email、token、invite_url等
    dify_email = db.Column(db.String(100), nullable=True)
    dify_token = db.Column(db.String(100), nullable=True)
    dify_invite_url = db.Column(db.String(500), nullable=True)
    # 其余数据
    created_at = db.Column('createdAt', db.TIMESTAMP, nullable=False, default=datetime.now())
    updated_at = db.Column('updatedAt', db.TIMESTAMP, nullable=False, default=datetime.now())