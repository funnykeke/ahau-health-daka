# -*- coding: UTF-8 -*-
import base64
import json
import time
from random import random
import logging
import yaml
from lxml import etree
import requests
from PyRsa.pyb64 import Base64
from PyRsa.pyrsa import RsaKey
from apscheduler.schedulers.background import BlockingScheduler

logging.basicConfig(level=logging.INFO, format='%(asctime)s  %(message)s', datefmt='%a, %d %b %Y %H:%M:%S +0000',
                    filename='daka.log')
with open('settings.yaml', 'r', encoding='utf-8') as a:
    settings = yaml.load(a.read(), Loader=yaml.FullLoader)
    a.close()
getPublicKeyUrl = 'http://fresh.ahau.edu.cn/yxxt-v5/xtgl/login/getPublicKey.zf'  # 获取公钥
getKaptchaUrl = 'http://fresh.ahau.edu.cn/yxxt-v5/kaptcha'  # 获取验证码
loginUrl = 'http://fresh.ahau.edu.cn/yxxt-v5/web/xsLogin/checkLogin.zf'  # 登录
dakaUrl = 'http://fresh.ahau.edu.cn/yxxt-v5/web/jkxxtb/tbBcJkxx.zf'  # 打卡
detailUrl = 'http://fresh.ahau.edu.cn/yxxt-v5/web/jkxxtb/tbJkxx.zf'  # 个人信息

headers = {'Host': 'fresh.ahau.edu.cn',
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0',
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
           'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
           'Accept-Encoding': 'gzip, deflate',
           'Connection': 'keep-alive',
           'Upgrade-Insecure-Requests': '1',
           'Pragma': 'no-cache',
           'Cache-Control': 'no-cache'}
session = requests.Session()


def send(text, desp):  # 微信通知
    if settings['noticeWhether']:
        data = {'text': text, 'desp': desp}
        requests.post(f"{settings['wechatNoticeUrl']}", data=data)
    else:
        pass


def getLoginPostData(mes, data):  # 用于登录
    rsakey = RsaKey()
    rsakey.set_public(Base64().b64tohex(mes['modulus']), Base64().b64tohex(mes['exponent']))
    enPassword = Base64().hex2b64(rsakey.rsa_encrypt(data['mm']))
    enZh = Base64().hex2b64(rsakey.rsa_encrypt(data['zh']))
    enZhlx = Base64().hex2b64(rsakey.rsa_encrypt(data['zhlx']))
    enYzm = Base64().hex2b64(rsakey.rsa_encrypt(data['yzm']))
    dldata = base64.b64encode(
        json.dumps({"zhlx": enZhlx, "zh": enZh, "mm": enPassword, "yzm": enYzm}).replace(' ', '').encode(
            "utf-8")).decode('utf-8')
    return {"dldata": dldata}


def discern(uname, pwd):  # 验证码识别
    result = {}
    while True:
        try:
            data = {"username": uname, "password": pwd, "image": base64.b64encode(session.get(getKaptchaUrl).content).decode(),
                    "typeid": 11}
            result = json.loads(requests.post(settings['discernUrl'], json=data).text)
            code = result["data"]["result"]
            break
        except:
            send('验证码异常', str(result))
            time.sleep(60)
    return code


def daka(student):
    global session
    session.headers.update(headers)
    while True:  # 用户登录
        try:
            yzm = discern(uname=settings['uname'], pwd=settings['pwd'])  # 验证码
            mes = session.get(getPublicKeyUrl).json()
            data = {'zhlx': 'xsxh', 'zh': str(student['xh']), 'mm': str(student['mm']), 'yzm': yzm}  # 登录信息
            LoginPostData = getLoginPostData(mes, data)
            if session.post(loginUrl, data=LoginPostData).json()['status'] == 'SUCCESS':
                logging.info(f"{student['xh']}登录成功")
                break
            else:
                pass
        except Exception as e:
            send("健康打卡异常", f'{student["xh"]}登录出错 异常：{e}')
            time.sleep(100)
    session.headers.update({
        'Cookie': f'JSESSIONID={session.cookies.get("JSESSIONID")}; cookiesession1={session.cookies.get("cookiesession1")}',
        'Referer': f'http://fresh.ahau.edu.cn/yxxt-v5/web/xsLogin/login.zf;jsessionid={session.cookies.get("JSESSIONID")}'})
    html = etree.HTML(session.get(detailUrl).text)
    session.headers.update({
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Length': '425', 'Origin': 'http://fresh.ahau.edu.cn',
        'Referer': 'http://fresh.ahau.edu.cn/yxxt-v5/web/jkxxtb/tbJkxx.zf', 'Accept': '*/*',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', })
    try:
        if (session.post(dakaUrl,
                         data={'xh': html.xpath('//input[@id="xh"]/@value')[0],
                               'xm': html.xpath('//input[@id="xm"]/@value')[0],
                               'sjdks': html.xpath('//input[@id="sjdks"]/@value')[0],
                               'sjdjs': html.xpath('//input[@id="sjdjs"]/@value')[0],
                               'tbsj': html.xpath('//input[@id="tbsj"]/@value')[0],
                               'tbzt': html.xpath('//input[@id="tbzt"]/@value')[0],
                               'jlid': html.xpath('//input[@id="jlid"]/@value')[0],
                               'dqrq': html.xpath('//input[@id="dqrq"]/@value')[0],
                               'sjdfgbz': html.xpath('//input[@id="sjdfgbz"]/@value')[0],
                               'sjdbz': html.xpath('//input[@id="sjdbz"]/@value')[0],
                               'tw': '36.{}'.format(int(random() * 8) + 1),
                               'dqszdmc': str(student['dqszdmc']),
                               'dqszsfdm': str(student['dqszsfdm']),
                               'dqszsdm': str(student['dqszsdm']),
                               'dqszxdm': str(student['dqszxdm']),
                               'bz': '正常',
                               'ydqszsfmc': '',
                               'ydqszsmc': '',
                               'ydqszxmc': ''}).json()['status'] == 'success'):
            logging.info(f'''{html.xpath('//input[@id="xm"]/@value')[0]}打卡成功''')
        else:
            send("健康打卡", f'''{html.xpath('//input[@id="xm"]/@value')[0]}打卡失败''')
    except Exception as e:
        send("健康打卡", f'{student["xh"]}打卡异常 异常：{e}')
    session.headers.clear()
    session.cookies.clear()


def run():
    with open('students.yaml', 'r', encoding='utf-8') as s:
        students = yaml.load(s.read(), Loader=yaml.FullLoader)
        s.close()
    for student in students:
        daka(student)


if __name__ == '__main__':
    scheduler = BlockingScheduler()
    scheduler.add_job(run, 'cron', hour=7)  # 早
    scheduler.add_job(run, 'cron', hour=12)  # 中
    scheduler.add_job(run, 'cron', hour=19)  # 晚
    scheduler.start()
    # run()
