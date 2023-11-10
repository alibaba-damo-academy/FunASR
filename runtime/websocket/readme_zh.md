# FunASR离线文件转写服务开发指南([点击此处](../docs/SDK_advanced_guide_offline_zh.md))

# FunASR实时语音听写服务开发指南([点击此处](../docs/SDK_advanced_guide_online_zh.md))

# 如果您想自己编译文件，可以参考下述步骤
## Linux/Unix 平台编译
### 下载 onnxruntime
```shell
wget https://github.com/microsoft/onnxruntime/releases/download/v1.14.0/onnxruntime-linux-x64-1.14.0.tgz
tar -zxvf onnxruntime-linux-x64-1.14.0.tgz
```

### 下载 ffmpeg
```shell
wget https://isv-data.oss-cn-hangzhou.aliyuncs.com/ics/MaaS/ASR/dep_libs/ffmpeg-N-111383-g20b8688092-linux64-gpl-shared.tar.xz
tar -xvf ffmpeg-N-111383-g20b8688092-linux64-gpl-shared.tar.xz
```

### 安装依赖
```shell
# openblas
sudo apt-get install libopenblas-dev #ubuntu
# sudo yum -y install openblas-devel #centos

# openssl
apt-get install libssl-dev #ubuntu 
# yum install openssl-devel #centos
```

### 编译 runtime

```shell
git clone https://github.com/alibaba-damo-academy/FunASR.git && cd FunASR/runtime/websocket
mkdir build && cd build
cmake  -DCMAKE_BUILD_TYPE=release .. -DONNXRUNTIME_DIR=/path/to/onnxruntime-linux-x64-1.14.0 -DFFMPEG_DIR=/path/to/ffmpeg-N-111383-g20b8688092-linux64-gpl-shared
make -j 4
```


## Windows 平台编译
### 下载 onnxruntime
https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-\shared.zip

下载并解压到 d:\ffmpeg-master-latest-win64-gpl-shared

### 下载 ffmpeg
https://github.com/microsoft/onnxruntime/releases/download/v1.16.1/onnxruntime-win-x64-1.16.1.zip

下载并解压到 d:\onnxruntime-win-x64-1.16.1

### 编译 openssl
https://www.openssl.org/source/openssl-1.1.1w.tar.gz 

下载解压到 d:/src/openssl-1.1.1w

打开 x64 Native Tools Command Prompt 执行以下编译步骤
```
d:
cd d:/src/openssl-1.1.1w
perl Configure VC-WIN64A --prefix=d:/openssl-1.1.1w
nmake
namke install

```

### 编译 runtime
```
git clone https://github.com/alibaba-damo-academy/FunASR.git 
cd FunASR/runtime/websocket
mkdir build
cd build
cmake ../ -D OPENSSL_ROOT_DIR=d:/openssl-1.1.1w -D FFMPEG_DIR=d:/ffmpeg-master-latest-win64-gpl-shared -D ONNXRUNTIME_DIR=d:/onnxruntime-win-x64-1.16.1
```
Visual Studio 打开 FunASRWebscoket.sln 完成编译

