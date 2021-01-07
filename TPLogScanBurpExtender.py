# coding:utf-8
import os
import datetime
import time
import re
import urllib2
import urlparse
import threading
from threading import Lock

from burp import IBurpExtender
from burp import IContextMenuFactory
from burp import ITab
from burp import IHttpListener
from burp import IMessageEditorController

from javax.swing import JMenu
from javax.swing import JMenuItem
from javax.swing import JPanel
from javax.swing import JScrollPane
from javax.swing import JSplitPane
from javax.swing import JTabbedPane
from javax.swing import ScrollPaneConstants
from javax.swing import SwingUtilities
from javax.swing import JTable
from javax.swing.table import AbstractTableModel

from java.awt import BorderLayout, GridLayout
from java.awt.event import ComponentEvent
from java.awt.event import ComponentListener

from java.io import PrintWriter
from java.util import Vector
from java.util import ArrayList

class BurpExtender(IBurpExtender, IContextMenuFactory, ITab, IHttpListener, IMessageEditorController, AbstractTableModel):
    def registerExtenderCallbacks(self, callbacks):
        self.messages = []

        self._callbacks = callbacks
        self._helpers = callbacks.getHelpers()
        self._callbacks.setExtensionName('TPLogScan')

        self._log = ArrayList()
        self._lock = Lock()

        self.jSplitPaneV = JSplitPane(JSplitPane.VERTICAL_SPLIT, True)
        self.jSplitPaneV.setDividerLocation(300)
        self.jSplitPaneV.setOneTouchExpandable(True)

        self.jPanel_top = JPanel()
        self.jTabbedPane = JTabbedPane(JTabbedPane.TOP)

        self.iRequestTextEditor = self._callbacks.createMessageEditor(self, False)
        self.iResponseTextEditor = self._callbacks.createMessageEditor(self, False)

        self.jTable = CustomTable(self)
        self.jTable.setShowGrid(True)
        self.jTable.setAutoCreateRowSorter(True)
        self.jTable.setAutoResizeMode(JTable.AUTO_RESIZE_SUBSEQUENT_COLUMNS)

        first_column_model = self.jTable.getColumnModel().getColumn(0)
        first_column_model.setPreferredWidth(60);
        first_column_model.setMaxWidth(60)
        first_column_model.setMinWidth(60)
        self.jTable.getColumnModel().getColumn(1).setPreferredWidth(300)

        third_column_model = self.jTable.getColumnModel().getColumn(2)
        third_column_model.setPreferredWidth(100)
        third_column_model.setMinWidth(100)
        self.jTable.getColumnModel().getColumn(3).setPreferredWidth(600)
        self.jTable.getColumnModel().getColumn(4).setPreferredWidth(100)
        self.jTable.getColumnModel().getColumn(5).setPreferredWidth(100)

        self.jScrollPane1 = JScrollPane(self.jTable)
        self.jScrollPane1.setHorizontalScrollBarPolicy(ScrollPaneConstants.HORIZONTAL_SCROLLBAR_AS_NEEDED)
        self.jScrollPane1.setVerticalScrollBarPolicy(ScrollPaneConstants.VERTICAL_SCROLLBAR_AS_NEEDED)

        self.jTabbedPane.addTab("Log", self.jScrollPane1)

        self.jPanel_top.add(self.jTabbedPane)
        self.jPanel_top.setLayout(GridLayout(1,1))

        self.jSplitPaneInfo = JSplitPane(JSplitPane.HORIZONTAL_SPLIT, True)
        self.jSplitPaneInfo.setDividerLocation(650)
        self.jSplitPaneInfo.setOneTouchExpandable(True) 

        self.jPanel_reqInfo_left = JPanel()
        self.jPanel_respInfo_right = JPanel()

        self.jPanel_reqInfo_left.setLayout(BorderLayout())
        self.jPanel_respInfo_right.setLayout(BorderLayout())

        self.jPanel_reqInfo_left.add(self.iRequestTextEditor.getComponent(),
                        BorderLayout.CENTER)
        self.jPanel_respInfo_right.add(self.iResponseTextEditor.getComponent(),
                        BorderLayout.CENTER)

        self.jSplitPaneInfo.add(self.jPanel_reqInfo_left, JSplitPane.LEFT)
        self.jSplitPaneInfo.add(self.jPanel_respInfo_right, JSplitPane.RIGHT)

        self.jSplitPaneV.add(self.jPanel_top, JSplitPane.TOP)
        self.jSplitPaneV.add(self.jSplitPaneInfo, JSplitPane.BOTTOM)

        self._callbacks.customizeUiComponent(self.jSplitPaneV)
        self._callbacks.customizeUiComponent(self.jPanel_top)
        self._callbacks.customizeUiComponent(self.jTabbedPane)
        self._callbacks.customizeUiComponent(self.jTable)
        self._callbacks.customizeUiComponent(self.jScrollPane1)
        self._callbacks.customizeUiComponent(self.jSplitPaneInfo)
        self._callbacks.customizeUiComponent(self.jPanel_reqInfo_left)
        self._callbacks.customizeUiComponent(self.jPanel_respInfo_right)
        self._callbacks.addSuiteTab(self)


        self._callbacks.registerHttpListener(self)
        self._callbacks.registerContextMenuFactory(self)

        return

    def getTabCaption(self):
        return 'TPLogScan'

    def getUiComponent(self):
        return self.jSplitPaneV


    def getRowCount(self):
        try:
            return self._log.size()
        except:
            return 0

    def getColumnCount(self):
        return 6

    def getColumnName(self, columnIndex):
        if columnIndex == 0:
            return "#"
        if columnIndex == 1:
            return "Host"
        if columnIndex == 2:
            return "Method"
        if columnIndex == 3:
            return "URL"
        if columnIndex == 4:
            return "Status"
        if columnIndex == 5:
            return "Length"
        return ""

    def getValueAt(self, rowIndex, columnIndex):
        logEntry = self._log.get(rowIndex)
        url = logEntry._url.toString()
        url_parse = urlparse.urlparse(url)
        if url_parse.netloc.find(':') != -1:
            netloc = url_parse.netloc[:url_parse.netloc.find(':')]
        host = url_parse.scheme + '://' + netloc
        path = url_parse.path
        if columnIndex == 0:
            return rowIndex+1
        if columnIndex == 1:
            return host
        if columnIndex == 2:
            return logEntry._method
        if columnIndex == 3:
            return path
        if columnIndex == 4:
            return logEntry._status_code
        if columnIndex == 5:
            return logEntry._length
        return ""

    def processHttpMessage(self, toolFlag, messageIsRequest, messageInfo):
        # tool_name = self._callbacks.getToolName(toolFlag)
        # if tool_name != 'Extender':
        if toolFlag != 1024:
            return
        if messageIsRequest:
            return
        request_info = self._helpers.analyzeRequest(messageInfo)
        response_info = self._helpers.analyzeResponse(messageInfo.getResponse())
        response_headers = response_info.getHeaders()
        response_length = 0
        for header in response_headers:
            header = header.encode('utf-8')
            if header.startswith("Content-Length"):
                response_length = int(header.replace('Content-Length: ', ''))

        length = response_length if response_length > 0 else 0

        self._lock.acquire()
        row = self._log.size()
        self._log.add(LogEntry(toolFlag, self._callbacks.saveBuffersToTempFiles(messageInfo), request_info.getUrl(),request_info.getMethod(),response_info.getStatusCode(),length))
        self.fireTableRowsInserted(row, row)
        self._lock.release()

    
    def getHttpService(self):
        return self._currentlyDisplayedItem.getHttpService()

    def getRequest(self):
        return self._currentlyDisplayedItem.getRequest()

    def getResponse(self):
        return self._currentlyDisplayedItem.getResponse()

    def loadMenus(self):
        self.menus = []
        self.mainMenu = JMenu("TPLogScan")
        self.menus.append(self.mainMenu)
        menu = JMenuItem('ThinkPHP v3', None, actionPerformed=lambda x: self.eventHandler(x))
        self.mainMenu.add(menu)
        menu = JMenuItem('ThinkPHP v5', None, actionPerformed=lambda x: self.eventHandler(x))
        self.mainMenu.add(menu)

    def createMenuItems(self, invocation):
        self.loadMenus()
        self.messages = invocation.getSelectedMessages()
        return self.menus if self.menus else None

    def eventHandler(self, x):
        menuName = x.getSource().text
        if menuName == 'ThinkPHP v3':
            version = 3
        elif menuName == 'ThinkPHP v5':
            version = 5
        else:
            print("chose error")
            return 

        for message in self.messages:
            url = str(self._helpers.analyzeRequest(message).getUrl())
            url_parse = urlparse.urlparse(url)
            url = url_parse.scheme + '://' + url_parse.netloc
            print("[*] url: {}".format(url))

            datetime_now = datetime.datetime.now()
            year = (datetime_now - datetime.timedelta(days=10)).year
            month = (datetime_now - datetime.timedelta(days=10)).month
            day = (datetime_now - datetime.timedelta(days=10)).day

            tplogscan  = TPLogScan(url, version, year, month, day)
            log_path = tplogscan.checkLogPath()
            if not log_path:
                print("[-] {} can't get log file! ".format(url))
                self._callbacks.issueAlert("{} can't get log file".format(url))
                return

            filename_list = tplogscan.genFileName()
            t = threading.Thread(target=self.logScan, args=(message, version, log_path, filename_list))
            t.start()

    def logScan(self, message, version, log_path, filename_list):
        http_service = message.getHttpService()
        old_request = self._helpers.bytesToString(message.getRequest())
        old_path = self._helpers.analyzeRequest(message).getUrl().getPath()
        for filename in filename_list:
            try:
                new_request = old_request.replace(" " + old_path + " HTTP/", " " + log_path+filename + " HTTP/")
                response, status_code = self.sendRequest(http_service, new_request)
                if status_code != 200:
                    continue
                tmp_filename = filename
                now_filename = ''
                pattern = re.compile(r"\[ (\d{4}-\d{2}-\d{2})T((\d{2}:){2}\d{2})\+08:00 \]")
                flag = True
                while flag:
                    match_result = pattern.search(response)
                    if not match_result:
                        break
                    time_str = match_result.group(1) + ' ' + match_result.group(2)
                    timeArray = time.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    timestamp = int(time.mktime(timeArray))
                    timestamp_list = [str(timestamp), str(timestamp-1), str(timestamp-2), str(timestamp-3)]
                    for timestamp in timestamp_list:
                        if version == 3:
                            tmp_filename = timestamp + '-' + filename
                        else:
                            tmp_filename = filename[:filename.find('/')] + '/' + timestamp + '-' + filename[filename.find('/')+1:]
                        if tmp_filename == now_filename:
                            flag = False
                            break
                        new_request = old_request.replace(" " + old_path + " HTTP/", " " + log_path+tmp_filename + " HTTP/")
                        response, status_code = self.sendRequest(http_service, new_request)
                        if status_code == 200:
                            now_filename = tmp_filename
                            flag = False
                            break
            except Exception as e:
                print("[-] error: {}".format(e))
        print('[*] Log Scan complete!')

    def sendRequest(self, http_service, new_request):
        checkRequestResponse = self._callbacks.makeHttpRequest(http_service, self._helpers.stringToBytes(new_request))
        status_code = self._helpers.analyzeResponse(checkRequestResponse.getResponse()).getStatusCode()
        print('[*] {} | {}'.format(self._helpers.analyzeRequest(checkRequestResponse).getUrl(), status_code))
        return self._helpers.bytesToString(checkRequestResponse.getResponse()), status_code


class CustomTable(JTable):
    def __init__(self, extender):
        self._extender = extender
        self.setModel(extender)
    
    def changeSelection(self, row, col, toggle, extend):
        logEntry = self._extender._log.get(self.convertRowIndexToModel(row))
        self._extender.iRequestTextEditor.setMessage(logEntry._requestResponse.getRequest(), True)
        self._extender.iResponseTextEditor.setMessage(logEntry._requestResponse.getResponse(), False)
        self._extender._currentlyDisplayedItem = logEntry._requestResponse
        
        JTable.changeSelection(self, row, col, toggle, extend)


class LogEntry:
    def __init__(self, tool, requestResponse, url, method, status_code, length):
        self._tool = tool
        self._requestResponse = requestResponse
        self._url = url
        self._method = method
        self._status_code = status_code
        self._length = length


class TPLogScan():
    def __init__(self, url, version, year, month, day):
        self.url = url
        self.version = version
        self.year = year
        self.month = month
        self.day = day
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:83.0) Gecko/20100101 Firefox/83.0'
        }

    def genFileName(self):
        version = self.version
        year = self.year
        month = self.month
        day = self.day
        now_year = datetime.datetime.now().year
        now_month = datetime.datetime.now().month
        now_day = datetime.datetime.now().day
        begin_date = datetime.date(year, month, day)
        end_date = datetime.date(now_year, now_month, now_day)
        date_list = [begin_date + datetime.timedelta(days=i) for i in range((end_date - begin_date).days+1)]
        filename_list = []
        for date in date_list:
            if version == 3:
                filename_list.append("{:0>2d}_{:0>2d}_{:0>2d}.log".format(int(str(date.year)[2:]), date.month, date.day))
            elif version == 5:
                filename_list.append("{}{:0>2d}/{:0>2d}.log".format(date.year, date.month, date.day))
        return filename_list

    def checkLogPath(self):
        url = self.url
        version = self.version
        log_path_list = {
            3: ['/Runtime/Logs/', '/App/Runtime/Logs/', '/Application/Runtime/Logs/Admin/', '/Application/Runtime/Logs/Home/', '/Application/Runtime/Logs/'],
            5: '/runtime/log/',
        }

        log_path = ''
        if version == 3:
            for path in log_path_list[version]:
                try:
                    response = ''
                    request = urllib2.Request(url+path, headers=self.headers)
                    response = urllib2.urlopen(request, timeout=20)
                    print('[*] Found {} log path: {} | status_code: {}'.format(url, path, response.code))
                    log_path = path
                    break
                except urllib2.URLError as e:
                    if hasattr(e, 'code'):
                        # print 'Error code:',e.code
                        if e.code == 403:
                            print('[*] Found {} log path: {} | status_code: {}'.format(url, path, e.code))
                            log_path = path
                            break
                    elif hasattr(e, 'reason'):
                        print('Reason:', e.reason)
                finally:
                    if response:
                        response.close()
        else:
            try:
                response = ''
                request = urllib2.Request(url+log_path_list[version], headers=self.headers)
                response = urllib2.urlopen(request, timeout=20)
                print('[*] Found {} log path: {} | status_code: {}'.format(url, log_path_list[version], response.code))
                log_path = log_path_list[version]
            except urllib2.URLError as e:
                if hasattr(e, 'code'):
                    # print 'Error code:',e.code
                    if e.code == 403:
                        print('[*] Found {} log path: {} | status_code: {}'.format(url, log_path_list[version], e.code))
                        log_path = log_path_list[version]
                elif hasattr(e, 'reason'):
                    print('Reason:', e.reason)
            finally:
                if response:
                    response.close()

        return log_path

    def saveLog2File(self, url, filename, data):
        dir_name = url.replace('https://', '').replace('http://', '').replace('/', '').replace(':', '_')
        data_path = 'TPLogData'
        if not os.path.isdir(data_path):
            os.mkdir(data_path)
        dir_path = os.path.join(data_path, dir_name)
        if not os.path.isdir(dir_path):
            os.mkdir(dir_path)

        with open(os.path.join(dir_path, filename.replace('/', '_')), 'w') as f:
            f.write(html)