#!/usr/bin/python
# coding=UTF-8
 
import urllib2
import urllib
import cookielib
import re
import random
import sys
import time
import pprint as pp
 
 
def log(msg):
    fn_log = '%s.log' % 'yc'
    fd_log = open(fn_log, 'a')
    msg = '[%s]: %s\n' % (time.strftime('%H:%M:%S'), str(msg))
    print msg
    fd_log.write(msg);
    fd_log.close()
 
def sendsms(dest,msg):
    #发送短信通知
    p=urllib.urlencode({'Msg':msg.decode('utf-8').encode('gbk')})
    url="http://xxx.xxx.xxx.xxx/send_sms?Dest="+dest+"&"+p
    send_rsp=urllib2.urlopen(url)
    if send_rsp.getcode() == 200:
        return send_rsp.read()
    else:
        return 'error:'+send_rsp.getcode
 
def yueche():
    #登陆,并获得约车信息(表单)页面地址
    yueche_form_url = login()
    yueche_form_urlopener = opener.open(yueche_form_url)
    if yueche_form_urlopener.getcode() == 200:
 
        #约车表单页面html内容
        data = yueche_form_urlopener.read()
        #log data
 
        #同样,获取表单的两个hidden字段值
        VIEWSTATE = re.findall('<input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="(.*)"', data)[0]
        EV = re.findall('<input type="hidden" name="__EVENTVALIDATION" id="__EVENTVALIDATION" value="(.*)"', data)[0]
 
        #遍历约车时段表单,取出约车按钮
        for line in data.split("\n"):
            #log line
 
            # 按钮,<input type="submit" name="GridView1$ctl02$I_HOUR13_17" value="0" onclick="return checkwall();" id="GridView1_ctl02_I_HOUR13_17" style="background-color:#00FFFF;height:30px;width:50px;" />
            # 含义:<input type="submit" name="约车时段按钮名" value="剩余约车数量" onclick="return checkwall();" id="GridView1_ctl02_I_HOUR13_17" style="background-color:#00FFFF;height:30px;width:50px;" />
            #注意:value值如为"数字+空格",则为已约好的时段的车号
            target=re.findall('<input type="submit" name="(GridView1\$ctl(\d\d)\$I_HOUR(13_17))" value="(\d*)"',line)
            if target:
                log(target)
 
                name=target[0][0]       #表单名
                day_add=target[0][1]        #日期加值
                lesson_time=target[0][2]    #课程时段
                value=target[0][3]      #可约车数量
 
                #如果可约车数量不为0， 约车
                if value != '0':
 
                    #组参数
                        p = urllib.urlencode({'__VIEWSTATE':VIEWSTATE, '__EVENTVALIDATION':EVENTVALIDATION, 'RadioButtonList1':'散段', name:value})
                        #log p
                        log('约车:'+name+':'+value)
                        yueche_rsq=opener.open(yueche_form_url,p)
                        if yueche_rsq.getcode()==200:
 
                        #约车成功,发送通知短信
                            yueche_data=yueche_rsq.read()
                            #log yueche_data
                            day=int(time.strftime('%d'))-2+int(day_add)
                            msg=time.strftime('%y-%m')+'-'+str(day)+'日'+lesson_time+'时段约车成功!'
                            log(msg)
                            log(sendsms(sys.argv[3],msg))
 
def login():
    #请求登陆表单页面
    login_form_urlopener = opener.open(url_root)
    if login_form_urlopener.getcode() == 200:
 
        #表单页面html内容
        data = login_form_urlopener.read()
        log(login_form_urlopener.info())
 
        #取得表单的两个hidden字段值(验证用?防止重复提交用?)
        VIEWSTATE = re.findall('id="__VIEWSTATE" value="(.*)"', data)[0]
        EVENTVALIDATION = re.findall('id="__EVENTVALIDATION" value="(.*)"', data)[0]
 
        #组登陆请求参数
        p = urllib.urlencode({'__VIEWSTATE':VIEWSTATE, '__EVENTVALIDATION':EVENTVALIDATION, 'txtname':sys.argv[1], 'txtpwd':sys.argv[2], 'button.x':random.randint(0, 99), 'button.y':random.randint(0, 99)})
        log(p)
 
        #提交表单
        login_action_urlopener = opener.open(login_action_url, p)
        if login_action_urlopener.getcode() == 200:
 
            #登陆结果页面内容
            action_data = login_action_urlopener.read()
            #log login_action_urlopener.info()
            #log action_data
 
            #约车页面地址为js的window.open跳转,获取地址
            m = re.findall("<script language='javascript'>window\.open\('(.*)','SubWindow", action_data)
            if m:
                log(m)
                yueche_form_url = url_root + m[0]
                log(yueche_form_url)
                return yueche_form_url
            else:
                log("login fail !!\n"+action_data)
    else:
        log('open login_form fail:' + str(login_form_urlopener.getcode()))

 
class CourseReservation(object):
    def __init__(self):
        self.url_root = 'http://114.251.109.215/WLYC'
        self.url_chkcode = '%s/image.aspx' % self.url_root
        self.url_login = '%s/XYYC21DR1.aspx' % self.url_root 
        self.url_cal = '%s/script/calendar.aspx' % self.url_root 

        self.restr_redirect_url = "language='javascript'>window\.open\('(.*)','SubWindow"
        self.restr_time_ticket = '<input type="submit" name="gv\$ctl(\d+)\$I_HOUR(\d+_\d+)" value="(\d+)"'
        self.restr_dates = '\<td\>\<font color="\#\d+"\>(\d+-\d+-\d+)\((.*)\)'
        self.restr_stat = '\<span id="lblMessage".*\<font color="Red" size="3"\>(.*)\<\/font\>'
         
        
        self.req = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))
        self.req.addheaders = [('User-agent', 'Mozilla/5.0 Gecko/20100101 Firefox/4.0b7'),
                               ('Connection', 'keep-alive'), ('Keep-Alive', 300)]

    def _getHiddenVals(self, page=None):
        self.VS = re.findall('id="__VIEWSTATE" value="(.*)"', page)[0]
        self.EV = re.findall('id="__EVENTVALIDATION" value="(.*)"', page)[0]

    def getCookie(self):
        print 'Getting Cookie & __VIEWSTATE & __EVENTVALIDATION ...'
        resp_root = self.req.open(self.url_root)
        if resp_root.getcode() == 200:
            page_root = resp_root.read()
            headers_resp = dict(resp_root.headers)
            self.cookie = headers_resp['set-cookie'].split('; ')[0]
            self.req.addheaders += [('Cookie', self.cookie)]
            print 'headers(opener): '; pp.pprint(self.req.addheaders)
            self._getHiddenVals(page_root)
        else:
            sys.exit('Failed to connect: %s' % self.url_root)

    def getChkcode(self):
        print 'Getting Check Code ...'
        resp_chkcode = self.req.open(self.url_chkcode)
        if resp_chkcode.getcode() == 200:
            headers_resp = dict(resp_chkcode.headers)
            # 'set-cookie': 'CheckCode=NNDB4; path=/, ImageV=NNDB4; path=/' 
            self.chkcode = headers_resp['set-cookie'].split('; ')[0].split('=')[1]
            self.cookie = '%s; CheckCode=%s; ImageV=%s' % (self.cookie, self.chkcode, self.chkcode)
            self.req.addheaders[-1] = ('Cookie', self.cookie)
            print 'headers(opener): '; pp.pprint(self.req.addheaders)
        else:
            sys.exit('Failed to connect: %s' % self.url_chkcode)

    def login(self, user_info=None):
        self.getCookie()
        self.getChkcode()
        # login POST data.
        if user_info and isinstance(user_info, dict):
            self.user = user_info['user']
            self.passwd = user_info['passwd']
            self.phase = user_info['phase']
        data_login = {'__VIEWSTATE': self.VS, '__EVENTVALIDATION': self.EV,
                   'RadioButtonList1': self.phase,
                   'txtname': self.user, 'txtpwd': self.passwd, 'yanzheng': self.chkcode,
                   'button.x': random.randint(0, 99), 'button.y': random.randint(0, 99)}
        data_urlencode = urllib.urlencode(data_login)
        pp.pprint(data_login)
        print 'Login ...'
        resp_login = self.req.open(self.url_login, data_urlencode)
        if resp_login.getcode() == 200:
            page_login = resp_login.read()
            path_login_redirect = re.findall(self.restr_redirect_url, page_login)[0]
            if path_login_redirect:
                self.url_timetable = '%s/%s' % (self.url_root, path_login_redirect)
            else:
                self.url_timetable = '%s/%s' % (self.url_root, 'aspx/car/XYYC22.aspx')
            print 'Redirecting to: %s' % path_login_redirect

    def showTimetable(self, refresh=False):
        """ refresh: first-time fetch or refresh a page.
                    1)True -- same page refresh with same phase refresh. 
                    2)False-- 1st-time fetching.
                    3)0-3 -- same page with different phase. 0:模拟机,1:散段,2:综合训练.
        """
        if refresh is False: 
            resp_login = self.req.open(self.url_timetable)
            print 'Getting time table ...'
        else:
            self._getHiddenVals(self.page_timetable)
            target_refresh = 'RadioButtonList1$%s'%refresh if refresh != 'True' else ''
            data_refresh = {'__VIEWSTATE': self.VS, '__EVENTTARGET=': target_refresh, 
                            '__EVENTARGUMENT=': '', '__LASTFOCUS=': ''}
            data_urlencode = urllib.urlencode(data_refresh)
            resp_login = self.req.open(self.url_timetable, data_urlencode)
            print 'Refreshing time table: %s' % target_refresh
        if resp_login.getcode() == 200:
            self.page_timetable = resp_login.read()
            status = re.findall(self.restr_stat, self.page_timetable)[0]
            print 'Status: %s' % status
            # <input type="submit" name="gv$ctl08$I_HOUR19_21" value="94" ...
            # tickets: [(date_id, hour_win, num_tickets]
            tickets = re.findall(self.restr_time_ticket, self.page_timetable)
            # dates: {date(2011-09-30): day of week(chinese)}
            dates = dict(re.findall(self.restr_dates, self.page_timetable))
            date_ids = list(set([ x[0] for x  in tickets ]))
            date_ids.sort()
            dates_keys = dates.keys()
            dates_keys.sort()
            self.map_id_dates = dict(zip(date_ids, dates_keys))
            # reserv_table: {date: [{hour_window: num_tickets}, ...]}
            self.reserv_table = {}
            for x in tickets:
                self.reserv_table.setdefault(self.map_id_dates[x[0]], {})[x[1]] = int(x[2])
            if self.reserv_table: pp.pprint(self.reserv_table)

    def orderTicket(self, time=None):
        self._getHiddenVals(self.page_timetable)
        map_date_id = dict([ (self.map_id_dates[k],k) for k in self.map_id_dates ])
        date = time['date']; hour = time['hour']
        # id_button: gv$ctl08$I_HOUR17_19
        id_button = 'gv$ctl%s$I_HOUR%s' % (map_date_id[date], hour)
        num_tickets = self.reserv_table[date][hour]
        data_order = {'__VIEWSTATE': self.VS, '__EVENTVALIDATION': self.EV,
                      'RadioButtonList1': self.phase, id_button: num_tickets}
        data_urlencode = urllib.urlencode(data_order)
        #pp.pprint(data_order)
        print 'Making reservation: %s' % time
        resp_order = self.req.open(self.url_timetable, data_urlencode)
        if resp_order.getcode() == 200:
            self.page_timetable = resp_order.read()
            status = re.findall(self.restr_stat, self.page_timetable)[0]
            print 'Status: %s' % status


if __name__ == '__main__':
    users = {'yxt': {'user': '11041536',
                   'passwd': '05070',
                    'phase': '散段',},
             'lvj': {'user': '11041539',
                   'passwd': '02190',
                    'phase': '散段',} }
    timeplan = {'yxt': [{'date': '2011-09-24',
                      'hour': '19_21'}], }
    time_order['lvj'] = time_order['yxt']

    aDfssCourse = CourseReservation()
    aDfssCourse.login(user_info=users['yxt'])
    aDfssCourse.showTimetable()
    aDfssCourse.showTimetable(refresh=0) # 0:模拟机,1:散段,2:综合训练.
    #for day in timeplan['yxt']:
    #    aDfssCourse.orderTicket(time=day)
    #aDfssCourse.showTimetable(refresh=True)
