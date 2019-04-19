import pycurl
import os
from io import *

import sys
libcurl_dir = r"tools\libcurl_win64"
sys.path.append(libcurl_dir)

try:
    c = pycurl.Curl()
    b = BytesIO()
    c.setopt(pycurl.WRITEFUNCTION, b.write)
    c.setopt(c.URL, 'https://baidu.com')
    c.setopt(pycurl.SSL_VERIFYPEER, 1)
    c.setopt(pycurl.SSL_VERIFYHOST, 2)
    # <TIPS>windows 要指定证书的路径不然会出现(77, "SSL: can't load CA certificate file E:\\curl\\ca-bundle.crt")
    # 证书路径就在curl下载的压缩包里面。mac/linux下面可以注释掉。
    c.setopt(pycurl.CAINFO, os.path.join(libcurl_dir, "curl-ca-bundle.crt"))
    # </TIPS>
    c.perform()
    result = b.getvalue().decode("utf-8")
    print(result)
except BaseException as e:
    print(e)
finally:
    b.close()
    c.close()
