"""
下载ECDICT英语词典数据库

ECDICT是一个开源的英语词典数据库，包含150万+英文单词及短语。
GitHub: https://github.com/skywind3000/ECDICT
"""

import os
import sys
import urllib.request


def download_ecdict():
    """下载ECDICT数据库到项目根目录"""
    # 获取项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    target_path = os.path.join(project_root, "ecdict.db")

    # 检查是否已存在
    if os.path.exists(target_path):
        print(f"词典数据库已存在: {target_path}")
        file_size = os.path.getsize(target_path) / (1024 * 1024)
        print(f"文件大小: {file_size:.2f} MB")
        response = input("是否重新下载？(y/N): ")
        if response.lower() != 'y':
            print("取消下载")
            return

    # ECDICT数据库下载地址
    # 可以从以下地址下载：
    # 1. GitHub Release (推荐): https://github.com/skywind3000/ECDICT/releases
    # 2. 百度网盘等国内镜像
    url = "https://github.com/skywind3000/ECDICT/releases/download/1.0.28/ecdict-sqlite-28.zip"

    print("=" * 60)
    print("ECDICT 数据库下载说明")
    print("=" * 60)
    print(f"\n由于文件较大（约150MB压缩包，解压后约450MB），")
    print("请手动下载并解压到项目根目录：\n")
    print(f"下载地址: {url}")
    print(f"\n或访问: https://github.com/skywind3000/ECDICT/releases")
    print(f"\n下载后将 stardict.db 或 ecdict.db 文件放置到：")
    print(f"{target_path}\n")
    print("=" * 60)

    # 尝试自动下载（如果网络允许）
    response = input("\n是否尝试自动下载？(可能较慢) (y/N): ")
    if response.lower() == 'y':
        try:
            print(f"\n开始下载到: {target_path}")
            print("这可能需要几分钟，请耐心等待...\n")

            def report_progress(block_num, block_size, total_size):
                downloaded = block_num * block_size
                percent = min(downloaded * 100 / total_size, 100)
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                print(f"\r下载进度: {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end='')

            zip_path = target_path + ".zip"
            urllib.request.urlretrieve(url, zip_path, reporthook=report_progress)
            print("\n\n下载完成！正在解压...")

            # 解压zip文件
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 查找.db文件
                db_files = [f for f in zip_ref.namelist() if f.endswith('.db')]
                if db_files:
                    # 解压第一个.db文件到目标路径
                    with zip_ref.open(db_files[0]) as source:
                        with open(target_path, 'wb') as target:
                            target.write(source.read())
                    print(f"解压完成: {target_path}")
                else:
                    print("错误: 压缩包中未找到.db文件")

            # 删除zip文件
            os.remove(zip_path)
            print("词典数据库安装成功！")

        except Exception as e:
            print(f"\n下载失败: {e}")
            print("\n请手动下载并解压到项目根目录")
            sys.exit(1)


if __name__ == "__main__":
    download_ecdict()
