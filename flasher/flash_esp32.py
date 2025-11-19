#!/usr/bin/env python3
"""
ESP32 원터치 플래싱 스크립트
Windows/Linux/Mac 모두 지원
"""

import os
import sys
import subprocess
import platform
import urllib.request
import tempfile
import argparse
from pathlib import Path

# 색상 출력 (Windows 지원)
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    
    @staticmethod
    def init():
        """Windows에서 색상 지원 활성화"""
        if platform.system() == 'Windows':
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except:
                pass

Colors.init()

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.RESET}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")

def find_esptool():
    """esptool.py 경로 찾기"""
    # 여러 가능한 경로 확인
    possible_paths = [
        'esptool.py',
        'esptool',
        sys.executable.replace('python.exe', 'Scripts/esptool.exe').replace('python', 'bin/esptool'),
    ]
    
    # PATH에서 찾기
    try:
        result = subprocess.run(['where' if platform.system() == 'Windows' else 'which', 'esptool.py'], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
    except:
        pass
    
    # 직접 실행 가능한지 확인
    for path in possible_paths:
        try:
            result = subprocess.run([path, 'version'], capture_output=True, text=True)
            if result.returncode == 0:
                return path
        except:
            continue
    
    # Python 모듈로 실행
    try:
        result = subprocess.run([sys.executable, '-m', 'esptool', 'version'], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            return [sys.executable, '-m', 'esptool']
    except:
        pass
    
    return None

def find_esp32_ports():
    """ESP32 포트 찾기"""
    ports = []
    
    if platform.system() == 'Windows':
        # Windows: COM 포트 찾기
        import serial.tools.list_ports
        try:
            for port in serial.tools.list_ports.comports():
                ports.append(port.device)
        except ImportError:
            # pyserial이 없으면 기본 COM 포트 확인
            for i in range(1, 21):  # COM1~COM20
                port = f'COM{i}'
                if os.path.exists(port):
                    ports.append(port)
    else:
        # Linux/Mac: /dev/ttyUSB*, /dev/cu.usbserial-* 등
        import glob
        patterns = [
            '/dev/ttyUSB*',
            '/dev/ttyACM*',
            '/dev/cu.usbserial*',
            '/dev/cu.SLAB_USBtoUART*',
        ]
        for pattern in patterns:
            ports.extend(glob.glob(pattern))
    
    return sorted(set(ports))

def download_firmware(url, output_path=None):
    """URL에서 펌웨어 다운로드"""
    if output_path is None:
        # URL에서 파일명 추출
        filename = url.split('/')[-1]
        if '?' in filename:
            filename = filename.split('?')[0]
        output_path = os.path.join(tempfile.gettempdir(), filename)
    
    print_info(f"다운로드 중: {url}")
    print_info(f"저장 위치: {output_path}")
    
    try:
        urllib.request.urlretrieve(url, output_path)
        print_success(f"다운로드 완료: {output_path}")
        return output_path
    except Exception as e:
        print_error(f"다운로드 실패: {e}")
        return None

def run_esptool(esptool_path, port, command, *args, baud=None):
    """esptool 실행"""
    base_args = ['--chip', 'esp32', '--port', port]
    if baud:
        base_args.extend(['--baud', str(baud)])
    
    if isinstance(esptool_path, list):
        cmd = esptool_path + base_args + [command] + list(args)
    else:
        cmd = [esptool_path] + base_args + [command] + list(args)
    
    print_info(f"실행: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print_error(f"실행 실패:\n{result.stderr}")
        return False
    
    if result.stdout:
        print(result.stdout)
    return True

def erase_flash(esptool_path, port):
    """플래시 지우기"""
    print_info(f"[{port}] 플래시 지우는 중...")
    return run_esptool(esptool_path, port, 'erase_flash')

def write_flash(esptool_path, port, bootloader_path, partitions_path, firmware_path, baud=460800):
    """펌웨어 플래싱"""
    print_info(f"[{port}] 펌웨어 플래싱 중...")
    
    args = [
        '0x1000', bootloader_path,
        '0x8000', partitions_path,
        '0x10000', firmware_path
    ]
    
    return run_esptool(esptool_path, port, 'write_flash', *args, baud=baud)

def main():
    parser = argparse.ArgumentParser(description='ESP32 원터치 플래싱 스크립트')
    parser.add_argument('--port', '-p', help='ESP32 포트 (예: COM3 또는 /dev/cu.usbserial-*)')
    parser.add_argument('--bootloader', '-b', 
                       default='partition/esp32-dt-02.ino.bootloader.bin',
                       help='부트로더 파일 경로')
    parser.add_argument('--partitions', '-t',
                       default='partition/esp32-dt-02.ino.partitions.bin',
                       help='파티션 파일 경로')
    parser.add_argument('--firmware', '-f', 
                       default='https://github.com/superplace/firmware/raw/refs/heads/main/esp32-dt-02-v218.ino.bin',
                       help='펌웨어 파일 경로 또는 URL (기본값: 최신 펌웨어 URL)')
    parser.add_argument('--baud', default=460800, type=int,
                       help='업로드 속도 (기본값: 460800)')
    parser.add_argument('--no-erase', action='store_true',
                       help='플래시 지우기 건너뛰기')
    parser.add_argument('--keep-firmware', action='store_true',
                       help='다운로드한 펌웨어 파일 유지')
    
    args = parser.parse_args()
    
    # esptool 찾기
    print_info("esptool 찾는 중...")
    esptool_path = find_esptool()
    if not esptool_path:
        print_error("esptool.py를 찾을 수 없습니다.")
        print_info("설치 방법: pip install esptool")
        sys.exit(1)
    print_success(f"esptool 발견: {esptool_path}")
    
    # 포트 찾기
    if args.port:
        ports = [args.port]
    else:
        print_info("ESP32 포트 찾는 중...")
        ports = find_esp32_ports()
        if not ports:
            print_error("ESP32 포트를 찾을 수 없습니다.")
            print_info("포트를 수동으로 지정하세요: --port COM3")
            sys.exit(1)
        print_success(f"발견된 포트: {', '.join(ports)}")
    
    # 펌웨어 파일 처리
    firmware_path = args.firmware
    downloaded_firmware = None
    
    # URL인지 확인
    if firmware_path.startswith('http://') or firmware_path.startswith('https://'):
        firmware_path = download_firmware(firmware_path)
        if not firmware_path:
            sys.exit(1)
        downloaded_firmware = firmware_path
    
    # 파일 존재 확인
    if not os.path.exists(firmware_path):
        print_error(f"펌웨어 파일을 찾을 수 없습니다: {firmware_path}")
        sys.exit(1)
    
    # 부트로더 및 파티션 파일 경로 확인
    script_dir = Path(__file__).parent.absolute()
    bootloader_path = args.bootloader if os.path.isabs(args.bootloader) else script_dir / args.bootloader
    partitions_path = args.partitions if os.path.isabs(args.partitions) else script_dir / args.partitions
    
    if not os.path.exists(bootloader_path):
        print_error(f"부트로더 파일을 찾을 수 없습니다: {bootloader_path}")
        sys.exit(1)
    
    if not os.path.exists(partitions_path):
        print_error(f"파티션 파일을 찾을 수 없습니다: {partitions_path}")
        sys.exit(1)
    
    # 각 포트에 대해 플래싱
    success_count = 0
    for port in ports:
        print(f"\n{'='*60}")
        print_info(f"포트: {port}")
        print(f"{'='*60}")
        
        # 플래시 지우기
        if not args.no_erase:
            if not erase_flash(esptool_path, port):
                print_error(f"[{port}] 플래시 지우기 실패")
                continue
            print_success(f"[{port}] 플래시 지우기 완료")
        else:
            print_warning(f"[{port}] 플래시 지우기 건너뛰기")
        
        # 펌웨어 플래싱
        if write_flash(esptool_path, port, str(bootloader_path), str(partitions_path), 
                      firmware_path, args.baud):
            print_success(f"[{port}] 플래싱 완료!")
            success_count += 1
        else:
            print_error(f"[{port}] 플래싱 실패")
    
    # 정리
    if downloaded_firmware and not args.keep_firmware:
        try:
            os.remove(downloaded_firmware)
            print_info(f"임시 파일 삭제: {downloaded_firmware}")
        except:
            pass
    
    # 결과 요약
    print(f"\n{'='*60}")
    if success_count == len(ports):
        print_success(f"모든 플래싱 완료: {success_count}/{len(ports)}")
    else:
        print_warning(f"일부 실패: {success_count}/{len(ports)} 성공")
    print(f"{'='*60}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n취소되었습니다.")
        sys.exit(1)
    except Exception as e:
        print_error(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

