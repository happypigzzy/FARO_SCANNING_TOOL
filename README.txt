此脚本用于依照录屏检视重定位运动误差，在第十行输入视频地址运行即可
#######################################################
1、视频录制时窗口大小不能变化，选择区域中xyz即可计算
2、视频会自动切除前五秒，并且进行跳采样到480p，每五帧取样获取FARO cam2软件中偏移值信息
3、注意：程序会自动过滤-3到+3的数据
4、此脚本需要安装tesseract-OCR

This script is used to inspect relocation motion errors according to the screen recording. You can run it by entering the video address on line 10.
#######################################################
1. The window size cannot change during video recording; select the xyz area for calculation.
2. The video will automatically be trimmed for the first five seconds and resampled to 480p, taking every fifth frame to obtain offset value information from FARO cam2 software.
3. Note: The program will automatically filter data from -3 to 3.

