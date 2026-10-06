all: pwn pwn_debug

pwn: pwn.c
	gcc ./pwn.c -o pwn -fno-stack-protector -pie -fPIE -z noexecstack -O0 -w
	strip ./pwn

pwn_debug: pwn.c
	gcc ./pwn.c -o pwn_debug -fno-stack-protector -pie -fPIE -z noexecstack -O0 -g3

clean:
	rm -rf ./pwn ./pwn_debug
