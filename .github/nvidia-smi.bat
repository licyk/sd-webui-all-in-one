@echo off
rem fake nvidia-smi command
set CUDA_VER=12.9
set COMP_CAP=9.0

if "%1"=="--query-gpu=compute_cap" if "%2"=="--format=noheader,csv" goto NvCompCap
if "%1"=="--format=noheader,csv" if "%2"=="--query-gpu=compute_cap" goto NvCompCap
if "%*"=="--format=noheader,csv --query-gpu=compute_cap" goto NvCompCap
if "%*"=="--query-gpu=compute_cap --format=noheader,csv" goto NvCompCap
if "%1"=="-q" goto NvDetail
if "%1"=="" goto CommonInfo
goto CommonInfo


:CommonInfo
echo Fri Jul 11 11:14:32 2025
echo +-----------------------------------------------------------------------------------------+
echo ^| NVIDIA-SMI 572.83                 Driver Version: 572.83         CUDA Version: %CUDA_VER%     ^|  
echo ^|-----------------------------------------+------------------------+----------------------+
echo ^| GPU  Name                  Driver-Model ^| Bus-Id          Disp.A ^| Volatile Uncorr. ECC ^|
echo ^| Fan  Temp   Perf          Pwr:Usage/Cap ^|           Memory-Usage ^| GPU-Util  Compute M. ^|
echo ^|                                         ^|                        ^|               MIG M. ^|
echo ^|=========================================+========================+======================^|
echo ^|   0  NVIDIA GeForce RTX 4060 ...  WDDM  ^|   00000000:01:00.0 Off ^|                  N/A ^|
echo ^| N/A   49C    P8              2W /   94W ^|       1MiB /   8188MiB ^|      0%%      Default ^|
echo ^|                                         ^|                        ^|                  N/A ^|
echo +-----------------------------------------+------------------------+----------------------+
echo.
echo +-----------------------------------------------------------------------------------------+
echo ^| Processes:                                                                              ^|
echo ^|  GPU   GI   CI              PID   Type   Process name                        GPU Memory ^|
echo ^|        ID   ID                                                               Usage      ^|
echo ^|=========================================================================================^|
echo ^|  No running processes found                                                             ^|
echo +-----------------------------------------------------------------------------------------+
goto LeaveScript


:NvCompCap
echo %COMP_CAP%
goto LeaveScript


:NvDetail
echo ==============NVSMI LOG==============
echo.
echo Timestamp                                 : Fri Jul 11 11:06:04 2025
echo Driver Version                            : 572.83
echo CUDA Version                              : %CUDA_VER%
echo.
echo Attached GPUs                             : 1
echo GPU 00000000:01:00.0
echo     Product Name                          : NVIDIA GeForce RTX 4060 Laptop GPU
echo     Product Brand                         : GeForce
echo     Product Architecture                  : Ada Lovelace
echo     Display Mode                          : Disabled
echo     Display Active                        : Disabled
echo     Persistence Mode                      : N/A
echo     Addressing Mode                       : N/A
echo     MIG Mode
echo         Current                           : N/A
echo         Pending                           : N/A
echo     Accounting Mode                       : Disabled
echo     Accounting Mode Buffer Size           : 4000
echo     Driver Model
echo         Current                           : WDDM
echo         Pending                           : WDDM
echo     Serial Number                         : N/A
echo     GPU UUID                              : GPU-aaaaaa-aaaa-aa-aaaaa-aaaa-aaa
echo     Minor Number                          : N/A
echo     VBIOS Version                         : 95.07.24.00.44
echo     MultiGPU Board                        : No
echo     Board ID                              : 0x100
echo     Board Part Number                     : N/A
echo     GPU Part Number                       : 0000-000-00
echo     FRU Part Number                       : N/A
echo     Platform Info
echo         Chassis Serial Number             : N/A
echo         Slot Number                       : N/A
echo         Tray Index                        : N/A
echo         Host ID                           : N/A
echo         Peer Type                         : N/A
echo         Module Id                         : 1
echo         GPU Fabric GUID                   : N/A
echo     Inforom Version
echo         Image Version                     : G002.0000.00.03
echo         OEM Object                        : 2.0
echo         ECC Object                        : N/A
echo         Power Management Object           : N/A
echo     Inforom BBX Object Flush
echo         Latest Timestamp                  : N/A
echo         Latest Duration                   : N/A
echo     GPU Operation Mode
echo         Current                           : N/A
echo         Pending                           : N/A
echo     GPU C2C Mode                          : N/A
echo     GPU Virtualization Mode
echo         Virtualization Mode               : None
echo         Host VGPU Mode                    : N/A
echo         vGPU Heterogeneous Mode           : N/A
echo     GPU Reset Status
echo         Reset Required                    : Requested functionality has been deprecated
echo         Drain and Reset Recommended       : Requested functionality has been deprecated
echo     GPU Recovery Action                   : None
echo     GSP Firmware Version                  : N/A
echo     IBMNPU
echo         Relaxed Ordering Mode             : N/A
echo     PCI
echo         Bus                               : 0x01
echo         Device                            : 0x00
echo         Domain                            : 0x0000
echo         Device Id                         : 0x00000000
echo         Bus Id                            : 00000000:01:00.0
echo         Sub System Id                     : 0x00000000
echo         GPU Link Info
echo             PCIe Generation
echo                 Max                       : 4
echo                 Current                   : 1
echo                 Device Current            : 1
echo                 Device Max                : 4
echo                 Host Max                  : 4
echo             Link Width
echo                 Max                       : 8x
echo                 Current                   : 8x
echo         Bridge Chip
echo             Type                          : N/A
echo             Firmware                      : N/A
echo         Replays Since Reset               : 0
echo         Replay Number Rollovers           : 0
echo         Tx Throughput                     : 50 KB/s
echo         Rx Throughput                     : 50 KB/s
echo         Atomic Caps Outbound              : N/A
echo         Atomic Caps Inbound               : N/A
echo     Fan Speed                             : N/A
echo     Performance State                     : P8
echo     Clocks Event Reasons
echo         Idle                              : Active
echo         Applications Clocks Setting       : Not Active
echo         SW Power Cap                      : Not Active
echo         HW Slowdown                       : Not Active
echo             HW Thermal Slowdown           : Not Active
echo             HW Power Brake Slowdown       : Not Active
echo         Sync Boost                        : Not Active
echo         SW Thermal Slowdown               : Not Active
echo         Display Clock Setting             : Not Active
echo     Sparse Operation Mode                 : N/A
echo     FB Memory Usage
echo         Total                             : 8188 MiB
echo         Reserved                          : 231 MiB
echo         Used                              : 1 MiB
echo         Free                              : 7957 MiB
echo     BAR1 Memory Usage
echo         Total                             : 8192 MiB
echo         Used                              : 8164 MiB
echo         Free                              : 28 MiB
echo     Conf Compute Protected Memory Usage
echo         Total                             : N/A
echo         Used                              : N/A
echo         Free                              : N/A
echo     Compute Mode                          : Default
echo     Utilization
echo         GPU                               : 0 %%
echo         Memory                            : 0 %%
echo         Encoder                           : 0 %%
echo         Decoder                           : 0 %%
echo         JPEG                              : 0 %%
echo         OFA                               : 0 %%
echo     Encoder Stats
echo         Active Sessions                   : 0
echo         Average FPS                       : 0
echo         Average Latency                   : 0
echo     FBC Stats
echo         Active Sessions                   : 0
echo         Average FPS                       : 0
echo         Average Latency                   : 0
echo     DRAM Encryption Mode
echo         Current                           : N/A
echo         Pending                           : N/A
echo     ECC Mode
echo         Current                           : N/A
echo         Pending                           : N/A
echo     ECC Errors
echo         Volatile
echo             SRAM Correctable              : N/A
echo             SRAM Uncorrectable Parity     : N/A
echo             SRAM Uncorrectable SEC-DED    : N/A
echo             DRAM Correctable              : N/A
echo             DRAM Uncorrectable            : N/A
echo         Aggregate
echo             SRAM Correctable              : N/A
echo             SRAM Uncorrectable Parity     : N/A
echo             SRAM Uncorrectable SEC-DED    : N/A
echo             DRAM Correctable              : N/A
echo             DRAM Uncorrectable            : N/A
echo             SRAM Threshold Exceeded       : N/A
echo         Aggregate Uncorrectable SRAM Sources
echo             SRAM L2                       : N/A
echo             SRAM SM                       : N/A
echo             SRAM Microcontroller          : N/A
echo             SRAM PCIE                     : N/A
echo             SRAM Other                    : N/A
echo     Retired Pages
echo         Single Bit ECC                    : N/A
echo         Double Bit ECC                    : N/A
echo         Pending Page Blacklist            : N/A
echo     Remapped Rows
echo         Correctable Error                 : 0
echo         Uncorrectable Error               : 0
echo         Pending                           : No
echo         Remapping Failure Occurred        : No
echo         Bank Remap Availability Histogram
echo             Max                           : 64 bank(s)
echo             High                          : 0 bank(s)
echo             Partial                       : 0 bank(s)
echo             Low                           : 0 bank(s)
echo             None                          : 0 bank(s)
echo     Temperature
echo         GPU Current Temp                  : 50 C
echo         GPU T.Limit Temp                  : 37 C
echo         GPU Shutdown T.Limit Temp         : -12 C
echo         GPU Slowdown T.Limit Temp         : -2 C
echo         GPU Max Operating T.Limit Temp    : 0 C
echo         GPU Target Temperature            : 87 C
echo         Memory Current Temp               : N/A
echo         Memory Max Operating T.Limit Temp : N/A
echo     GPU Power Readings
echo         Average Power Draw                : N/A
echo         Instantaneous Power Draw          : 2.81 W
echo         Current Power Limit               : 93.42 W
echo         Requested Power Limit             : 93.42 W
echo         Default Power Limit               : 80.00 W
echo         Min Power Limit                   : 5.00 W
echo         Max Power Limit                   : 140.00 W
echo     GPU Memory Power Readings
echo         Average Power Draw                : N/A
echo         Instantaneous Power Draw          : N/A
echo     Module Power Readings
echo         Average Power Draw                : N/A
echo         Instantaneous Power Draw          : N/A
echo         Current Power Limit               : N/A
echo         Requested Power Limit             : N/A
echo         Default Power Limit               : N/A
echo         Min Power Limit                   : N/A
echo         Max Power Limit                   : N/A
echo     Power Smoothing                       : N/A
echo     Workload Power Profiles
echo         Requested Profiles                : N/A
echo         Enforced Profiles                 : N/A
echo     Clocks
echo         Graphics                          : 210 MHz
echo         SM                                : 210 MHz
echo         Memory                            : 405 MHz
echo         Video                             : 765 MHz
echo     Applications Clocks
echo         Graphics                          : N/A
echo         Memory                            : N/A
echo     Default Applications Clocks
echo         Graphics                          : N/A
echo         Memory                            : N/A
echo     Deferred Clocks
echo         Memory                            : N/A
echo     Max Clocks
echo         Graphics                          : 3105 MHz
echo         SM                                : 3105 MHz
echo         Memory                            : 8001 MHz
echo         Video                             : 2415 MHz
echo     Max Customer Boost Clocks
echo         Graphics                          : N/A
echo     Clock Policy
echo         Auto Boost                        : N/A
echo         Auto Boost Default                : N/A
echo     Voltage
echo         Graphics                          : N/A
echo     Fabric
echo         State                             : N/A
echo         Status                            : N/A
echo         CliqueId                          : N/A
echo         ClusterUUID                       : N/A
echo         Health
echo             Bandwidth                     : N/A
echo             Route Recovery in progress    : N/A
echo             Route Unhealthy               : N/A
echo             Access Timeout Recovery       : N/A
echo     Processes                             : None
echo     Capabilities
echo         EGM                               : disabled
goto LeaveScript


:LeaveScript
exit /B
