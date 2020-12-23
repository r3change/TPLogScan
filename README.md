ThinkPHP3和5全日志扫描脚本

### 安装

```
pip install -r requirements.txt
```

### 使用

```
python3 TPLogScan.py -h

usage: TPLogScan.py [-h] [-u URL] [-v {3,5}] [-y YEAR] [-m MONTH] [-d DAY]

Thinkphp 3 or 5 log file scan!

optional arguments:
  -h, --help            show this help message and exit
  -u URL, --url URL     target url
  -v {3,5}, --version {3,5}
                        thinkphp version, default 3
  -y YEAR, --year YEAR  datetime year, default 2020
  -m MONTH, --month MONTH
                        datetime month, default 1
  -d DAY, --day DAY     datetime day, default 1
```

扫描ThinkPHP3 1月-本月的网站所有日志
```
python3 TPLogScan.py -u URL
```

扫描ThinkPHP5 12月的网站所有日志
```
python3 TPLogScan.py -u URL -v 5 -m 12
```

扫描结果保存在 `/TPLogData/{URL}/` 目录下
![](log.jpg)
