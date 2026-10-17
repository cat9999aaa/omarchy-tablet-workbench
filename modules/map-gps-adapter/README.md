# 地图GPS按需适配插件 · 0.1.0

将已有gpsd服务接到Qt Positioning。Marble Maps26.08.0通过Qt默认位置源读取，因此仅在地图进程设置私有Qt插件目录；不修改系统Qt插件、不接管串口，不增加GPS守护进程。

状态：远程软件测试与平板隔离兼容通过；版本化私有插件和用户地图入口已部署。真实卫星fix、地图居中和触屏体验尚待验收。模拟位置通过不能证明本机卫星定位成功。

## 行为

- 工厂固定连接本机127.0.0.1:2947，订阅gpsd JSON；无任意远程地址或串口参数。
- 只接受TPV的2D/3D fix、数值型且范围合法的经纬度、带时区的新鲜时间。10秒前或5秒后的时间拒绝；明确失去fix、连接断开或超时后lastKnownPosition无效。部分TPV不抹掉已有新鲜定位，也不延长有效时间。
- 接收器仅随应用工作。连接失败5秒退避；定位更新由socket事件驱动。stop释放持续订阅；同时进行的单次请求按Qt规范继续至完成或超时。
- 单行16KiB、缓冲64KiB，异常数据不扩张内存。插件不记录位置、不向外部服务器连接。
- 地图本身的在线底图请求、缓存与偏好仍由上游应用负责，不能把插件本地传输解释为整个地图完全离线。

## 构建与入口

在授权远程环境或一次性CI机器使用Qt6Core、Network、Positioning、Test，CMake/Ninja。不要在平板批量编译。

```sh
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure
```

测试只连接临时本地TCP端口，使用人工坐标；工厂探针只创建默认源，不开始真实GPS订阅。`build/plugins/position/libworkbench_gpsd.so` 为产物。

版本目录包含 `release.json`（schema1、QtCore/Positioning的版本列表qt_versions、binary_sha256）和上述plugins子目录。发布前比对远程产物sha与本机Qt版本；启动器拒绝版本变更/文件损坏，不自动加载其他副本。

```sh
python3 launch.py --release /path/to/verified-release --check
python3 launch.py --release /path/to/verified-release
```

启动器不调用sudo、pkexec或GPS开关。先在现有网络面板按需开启定位，地图是否有卫星位置需另验。恢复时使用普通 `marble-maps` 启动即不带该进程的私有插件目录。用户“平板地图”入口使用私有版本启动器；没有修改系统desktop文件或增加自动启动。

来源依据：[Marble26.08.0](https://github.com/KDE/marble/blob/v26.08.0/src/apps/marble-maps/MainScreen.qml)、[Qt6定位扩展](https://doc.qt.io/qt-6/position-plugin-nmea.html)、[gpsd JSON协议](https://gpsd.io/gpsd_json.html)。原创GPL-3.0-only；Qt/Marble/gpsd为外部依赖，未复制其实现。

插件优先级2000高于当前Qt内置GeoClue2的1000，仅对本地图进程可见。使用干净构建目录发布，工厂探针校验实际二进制中的优先级，并连续30次独立启动确认默认源。Qt升级后启动器拒绝旧ABI，需重新远程构建验收。
