import datetime
import os
import sys
import time

import logger
from optparse import OptionParser
from multiprocessing import Process,JoinableQueue, Queue
import queue
import tftpy
from random import randint

my_logger = logger.getLogger("TftpStress")

download_file_names = [
    "BOOT",
    "boot_emmc-boot.scr",
    "boot_emmc-gpt.cmd",
    "boot_emmc-recovery.cmd",
    "boot_emmc-rootfs_rw.scr",
    "boot_emmc-system.scr",
    "data.1-of-1.gz",
    "partition16G_ro.xml",
    "rootfs.2-of-10.gz",
    "rootfs.6-of-10.gz",
    "rootfs_rw.1-of-1.gz",
    "system.3-of-8.gz",
    "system.7-of-8.gz",
    "boot.1-of-1.gz",
    "boot_emmc.cmd",
    "boot_emmc-gpt.scr",
    "boot_emmc-recovery.scr",
    "boot_emmc-rootfs.scr",
    "boot.scr",
    "fip.bin",
    "recovery.1-of-1.gz",
    "rootfs.3-of-10.gz",
    "rootfs.7-of-10.gz",
    "spi_flash.bin",
    "system.4-of-8.gz",
    "system.8-of-8.gz",
    "boot.cmd",
    "boot_emmc-data.cmd",
    "boot_emmc-misc.cmd",
    "boot_emmc-rootfs.cmd",
    "boot_emmc.scr",
    "boot_spif.cmd",
    "gpt.gz",
    "rootfs.10-of-10.gz",
    "rootfs.4-of-10.gz",
    "rootfs.8-of-10.gz",
    "system.1-of-8.gz",
    "system.5-of-8.gz",
    "tftp.MD",
    "boot_emmc-boot.cmd",
    "boot_emmc-data.scr",
    "boot_emmc-misc.scr",
    "boot_emmc-rootfs_rw.cmd",
    "boot_emmc-system.cmd",
    "boot_spif.scr",
    "misc.1-of-1.gz",
    "rootfs.1-of-10.gz",
    "rootfs.5-of-10.gz",
    "rootfs.9-of-10.gz",
    "system.2-of-8.gz",
    "system.6-of-8.gz"
]

def get_next_file():
    idx = randint(0, len(download_file_names)-1)
    return download_file_names[idx]

def tftp_downloader(name, rq, host, port, blksize, tsize, localip, timeout ):
    """
    post get_open_lock by process
    :param name:
    :param ip:
    :param group_id:
    :param total:
    :param delay:
    :return:
    """

    while True:
        name = get_next_file()
        output_name = "%s_dw" %(name)

        tftp_options = {}
        tftp_options['timeout'] = int(timeout)
        if blksize:
            tftp_options['blksize'] = int(blksize)
        if tsize:
            tftp_options['tsize'] = 0
        tclient = tftpy.TftpClient(host,
                               int(port),
                               tftp_options,
                               localip)

        class Progress(object):
            def __init__(self, out):
                self.progress = 0
                self.out = out

            def progresshook(self, pkt):
                if isinstance(pkt, tftpy.TftpPacketTypes.TftpPacketDAT):
                    self.progress += len(pkt.data)
                    #self.out("Transferred %d bytes" % self.progress)
                elif isinstance(pkt, tftpy.TftpPacketTypes.TftpPacketOACK):
                    #self.out("Received OACK, options are: %s" % pkt.options)
                    pass

        progresshook = Progress(my_logger.info).progresshook

        try:
                tclient.download(name,
                                 output_name,
                                 progresshook)
                rq.put('OK: %s' %(name))
        except tftpy.TftpException as err:
            sys.stderr.write("%s\n" % str(err))
            my_logger.error("下载出错，退出压测程序")
            sys.exit(1)
        except KeyboardInterrupt:
            pass



def statics(name, rq):

    ok_cnts = 0
    ng_cnts = 0
    to_cnts = 0
    while True:
        time.sleep(1)

def download_stress(max_tasks, host, port, blksize, tsize, localip,timeout):
    result_queue = Queue()
    processes = []

    #创建统计进程
    sp = Process(target=statics, args=("sp", result_queue))
    #创建下载进程
    for i in range(max_tasks):
        p = Process(target=tftp_downloader, args=("dp", result_queue, host, port, blksize, tsize,localip,timeout))
        processes.append(p)

    sp.start()
    for p in processes:
        p.start()
    sp.join()
    for p in processes:
        p.join()

def main():
    usage = ""
    parser = OptionParser(usage=usage)

    parser.add_option('-i',
                      '--host',
                      type='string',
                      help='server ip',
                      default="192.168.1.99")
    parser.add_option('-p',
                      '--port',
                      type='int',
                      help='tftp port (default: 69)',
                      default=69)
    parser.add_option('-b',
                      '--blksize',
                      type='int',
                      default=512,
                      help='udp packet size to use (default: 512)')
    parser.add_option('-n',
                      '--max_tasks',
                      type='int',
                      help='并发下载进程数量',
                      default=1)
    parser.add_option('-d',
                      '--max_download_speed',
                      type='int',
                      help='并发速度限制',
                      default=1)
    parser.add_option('-T',
                      '--timeout',
                      type='int',
                      help='超时设置',
                      default=7)
    parser.add_option('-t',
                      '--tsize',
                      action='store_true',
                      default=False,
                      help="ask client to send tsize option in download")
    parser.add_option('-l',
                      '--localip',
                      action='store',
                      dest='localip',
                      default="",
                      help='local IP for client to bind to (ie. interface)')
    options, args = parser.parse_args()

    download_stress(options.max_tasks, options.host, options.port, options.blksize, options.tsize, options.localip, options.timeout)


if __name__ == '__main__':
    main()

