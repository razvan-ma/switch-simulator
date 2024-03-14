Scheleton for the Hub implementation.

## Building the switch

```bash
make
```

## Running



```bash
sudo python3 sim/topo.py
```

This will open 4 terminals, 4 hosts and 1 hub. On the hub terminal you will run 

```bash
python3 hub.py
```

The hosts have the following IP addresses.
```
host0 192.168.1.0
host1 192.168.1.1
host2 192.168.1.2
host3 192.168.1.3
```

We will be testing using the ICMP. For example, from host0 we will run:

```
ping 192.168.1.2
```

Note: We will use wireshark for debugging. From any terminal you can run `wireshark&`.


## FAQ

Q: Pe WSL remane hanged `xrdb merge` sau, ulterior, imi dadea eroarea de autorizare.

A:    
* export DISPLAY=$(ipconfig.exe | awk '/IPv4/ {sub("\r",":0"); print $NF;exit}') in ~/.bashrc conform https://github.com/QMonkey/wsl-tutorial/issues/11#issuecomment-650833026

* instalarea de Windows X-Server - https://github.com/hubisan/emacs-wsl#install-windows-x-server-vcxsrv

* configurarile de firewall pe Windows - https://github.com/hubisan/emacs-wsl#install-windows-x-server-vcxsrv

* rularea XServer cu Disable Access Control - https://github.com/microsoft/WSL/issues/6430#issuecomment-917701104

Q: crapa  rularea lui hub.py cu ioctl SIOCGIFINDEX

A: restart la WSL
