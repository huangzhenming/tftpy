import os, sys, subprocess
import platform
import time

import paramiko
import pathlib
import tftpy
from optparse import OptionParser
import logger
import copy

devices = [
    "192.168.7.8",
    "192.168.7.9",
    "192.168.7.10",
    "192.168.0.107",
    "192.168.0.112",
    "192.168.0.117",
    "192.168.0.137",
    "192.168.0.243",
    "192.168.0.192",
    "192.168.0.218"
]

my_logger = logger.getLogger("BatchUpgrader")
class RemoteDeivce:
    def __init__(self, ip, username, password):
        self.ip = ip
        self._logger = logger.getLogger('main')
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(ip, 22, username, password, timeout=10)

    def execute(self, command):
        try:
            _, stdout, stderr = self.ssh.exec_command(command, get_pty=True)
            exit_status = stdout.channel.recv_exit_status()  # Blocking call
            for line in stderr.readlines():
                self._logger.debug(line.strip())
            return stdout.readlines()
        except Exception as e:
            self._logger.exception(e)

    def checksum(self, local, remote):
        try:
            ret0 = subprocess.check_output(['md5sum', local])
            _, ret1, _ = self.ssh.exec_command('md5sum %s' % remote)
            ret1 = ret1.readlines()[0]
            self._logger.debug( local+":"+ ret0[:32]+" vs "+ret1[:32])
            if ret0[:32] == ret1[:32]:
                return True
        except Exception:
            return False

    def close(self):
        self.ssh.close()

    @staticmethod
    def __progess(current, total):
        sys.stdout.write("\rTransferred: %d/%d" % (current, total))
        sys.stdout.flush()

    def download(self, local, remote):
        if self.checksum(local, remote):
            return
        self._logger( "*** download"+local)
        sftp = self.ssh.open_sftp()
        sftp.get(remote, local, callback=RemoteDeivce.__progess)
        sftp.close()
        self._logger.debug(" Done!")

    def upload(self, local, remote):
        if self.checksum(local, remote):
            return
        self._logger.info("*** upload" + local)
        sftp = self.ssh.open_sftp()
        sftp.put(local, remote, callback=RemoteDeivce.__progess)
        sftp.close()
        self._logger.debug(" Done!")

    def tftp_upgrade(self):
        command = 'sudo cp /home/linaro/boot.scr.emmc /boot/boot.scr.emmc'
        output = self.execute(command)
        if len(output) != 0:
            error_msg = "拷贝文件至/boot/boot.scr.emmc出错。Err： %s" %(output[0].strip())
            raise Exception(error_msg)
        else:
            my_logger.info("拷贝文件至 %s 成功" %(self.ip))

    def tftp_reboot(self):
        command = 'sudo reboot'
        output = self.execute(command)
        if len(output) != 0:
            error_msg = "重启目标机器时出错。Err： %s" %(output[0].strip())
            raise Exception(error_msg)
        else:
            my_logger.info("重启目标机器： %s" %(self.ip))

    def tftp_verify_upgrade(self):
        command = 'cat /system/data/buildinfo.txt'
        output = self.execute(command)
        if len(output) != 0 and "BUILD TIME" in output[0]:
            error_msg = "%s 正常连接，升级成功！" %(self.ip)
            my_logger.info(error_msg)
            return self.ip
        else:
            return None



def gen_uboot_image(gateip, ipaddr, netmask):
    """
    根据SE5 网络信息，产生相应的boot.scr.emmc文件
    :param ipaddr:
    :param netmask:
    :param gateip:
    :return: 成功则返回生成的文件名，失败返回None
    """
    ret = None
    cmd ="set ipaddr %s;set netmask %s;set serverip %s;set reset_after 1\ntftp 0x310000000 192.168.1.99:boot.scr\nsource 0x310000000"
    with open("boot.cmd", 'w', newline='\n') as f:
        f.write("set ipaddr %s;set netmask %s;set serverip %s;set reset_after 1\n" %(ipaddr, netmask, gateip))
        f.write("tftp 0x310000000 %s:boot.scr\n" %(gateip))
        f.write("source 0x310000000\n")

    system = platform.system()
    assert system in ['Windows', 'Linux']

    cur_dir = pathlib.Path(__file__).parent.absolute()
    boot_cmd = pathlib.Path.joinpath(cur_dir, 'boot.cmd')
    boot_scr_emmc = pathlib.Path.joinpath(cur_dir, 'boot.scr.emmc')
    cmd = []

    try:
        if system =='Windows':
            mkimage = pathlib.Path.joinpath(cur_dir, 'mkimage.exe')
            cmd.append(mkimage.__str__())
            cmd.append("-A")
            cmd.append("arm")   #windows下的mkimge工具的ARCH没有arm64, 此处使用arm生成
            cmd.append("-O")
            cmd.append("linux")
            cmd.append("-T")
            cmd.append("script")
            cmd.append("-C")
            cmd.append("none")
            cmd.append("-a")
            cmd.append("0")
            cmd.append("-e")
            cmd.append("0")
            cmd.append("-n")
            cmd.append("boot.cmd")
            cmd.append("-d")
            cmd.append("boot.cmd")
            cmd.append(boot_scr_emmc.__str__())
        elif system == 'Linux':
            mkimage = pathlib.Path.joinpath(cur_dir, 'mkimage')
            cmd.append(mkimage.__str__())
            cmd.append("-A")
            cmd.append("arm64")
            cmd.append("-O")
            cmd.append("linux")
            cmd.append("-T")
            cmd.append("script")
            cmd.append("-C")
            cmd.append("none")
            cmd.append("-a")
            cmd.append("0")
            cmd.append("-e")
            cmd.append("0")
            cmd.append("-n")
            cmd.append("boot.cmd")
            cmd.append("-d")
            cmd.append("boot.cmd")
            cmd.append(boot_scr_emmc.__str__())
        else:
            my_logger.error("不支持的操作系统，无法产生uboot image。当前支持 Windows 和 Linux")

        output = subprocess.check_output(cmd)
        # print(output.decode('utf-8'))
        ret = boot_scr_emmc.__str__()
    except subprocess.CalledProcessError as e:
        my_logger.critical("产生uboot image时出错。错误码： %s" %(e.returncode))
    except Exception as e:
        my_logger.exception(e)
    return  ret


def batch_upgrade(gateip, ipaddr, netmask, username, password):



    #产生boot.scr.emmc, 并上传到SE5进行升级
    for ip in devices:
        boot_scr_emmc = gen_uboot_image(gateip, ip, netmask)
        if boot_scr_emmc:
            try:
                rd = RemoteDeivce(ip, username, password)
                rd.upload(boot_scr_emmc, '/home/linaro/boot.scr.emmc')
                rd.tftp_upgrade()
                rd.tftp_reboot()
                my_logger.info("%s 开始升级..." %(ip))
            except Exception as e:
                my_logger.error("尝试升级%s时出错" %(ip))
                my_logger.critical(e)
        time.sleep(2)

    time.sleep(300)
    # 轮循检查SE5状态，确认升级成功
    max_retry_cnt = 100
    query_list = copy.deepcopy(devices)
    while (max_retry_cnt):
        for ip in query_list:
            try:
                rd = RemoteDeivce(ip, username, password)
                ret = rd.tftp_verify_upgrade()
                if (ret != None):
                    query_list.remove(ret)
            except Exception as e:
                my_logger.critical(e)
        max_retry_cnt -= 1
        if (len(query_list) == 0):
            break
        my_logger.info("cnt: %s" % max_retry_cnt)
        time.sleep(5)



def main():
    usage = ""
    parser = OptionParser(usage=usage)

    parser.add_option('-s',
                      '--gateip',
                      type='string',
                      help='tftp 服务器 ip',
                      default="192.168.1.99")
    parser.add_option('-i',
                      '--ipaddr',
                      type='string',
                      help='SE5 IP地址',
                      default="192.168.7.8")
    parser.add_option('-n',
                      '--netmask',
                      type='string',
                      help='SE5网络掩码',
                      default="255.255.240.0")
    parser.add_option('-u',
                      '--username',
                      type='string',
                      help='SE5登陆用户名',
                      default="linaro")
    parser.add_option('-p',
                      '--password',
                      type='string',
                      help='SE5登陆密码',
                      default="linaro")
    options, args = parser.parse_args()

    batch_upgrade(options.gateip, options.ipaddr, options.netmask, options.username, options.password)


if __name__ == '__main__':
    main()