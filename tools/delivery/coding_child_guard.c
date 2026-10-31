/* Source-only Linux x86_64 guard. Build with a reviewed native SHA256 macro.
 * Never setuid. All argument/path handling happens after the fixed setpriv drop.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <errno.h>
#include <fcntl.h>
#include <linux/audit.h>
#include <linux/capability.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <limits.h>

#define NATIVE "/usr/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex"
#define RUNTIME "/home/user/src/offmenu/.delivery/stokowski/"
#ifndef NATIVE_SHA256
#define NATIVE_SHA256 "UNCONFIGURED"
#endif
static _Noreturn void refuse(void) { fputs("coding confinement refused\n", stderr); exit(126); }

/* SHA256 for a regular root-controlled executable; no subprocess or package. */
static uint32_t rr(uint32_t x, unsigned n) { return (x>>n)|(x<<(32-n)); }
static void block(uint32_t h[8], const unsigned char *p) {
    static const uint32_t k[64]={
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
    uint32_t w[64],a=h[0],b=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],z=h[7];
    for(unsigned i=0;i<16;i++) w[i]=(uint32_t)p[4*i]<<24|(uint32_t)p[4*i+1]<<16|(uint32_t)p[4*i+2]<<8|p[4*i+3];
    for(unsigned i=16;i<64;i++) w[i]=w[i-16]+(rr(w[i-15],7)^rr(w[i-15],18)^(w[i-15]>>3))+w[i-7]+(rr(w[i-2],17)^rr(w[i-2],19)^(w[i-2]>>10));
    for(unsigned i=0;i<64;i++) {
        uint32_t t=z+(rr(e,6)^rr(e,11)^rr(e,25))+((e&f)^(~e&g))+k[i]+w[i];
        uint32_t u=(rr(a,2)^rr(a,13)^rr(a,22))+((a&b)^(a&c)^(b&c));
        z=g;g=f;f=e;e=d+t;d=c;c=b;b=a;a=t+u;
    }
    h[0]+=a;h[1]+=b;h[2]+=c;h[3]+=d;h[4]+=e;h[5]+=f;h[6]+=g;h[7]+=z;
}
static void hash_fd(int fd, char hex[65]) {
    uint32_t h[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    unsigned char buf[64]; size_t used=0; uint64_t total=0; ssize_t n;
    while((n=read(fd,buf+used,64-used))>0) {
        used+=(size_t)n; total+=(uint64_t)n;
        if(used==64) { block(h,buf);used=0; }
    }
    if(n<0) refuse();
    buf[used++]=0x80;
    if(used>56) { memset(buf+used,0,64-used);block(h,buf);used=0; }
    memset(buf+used,0,56-used);
    for(unsigned i=0;i<8;i++) buf[63-i]=(unsigned char)((total*8)>>(8*i));
    block(h,buf);
    for(unsigned i=0;i<8;i++) snprintf(hex+8*i,9,"%08x",h[i]);
}

/* Read-only context verification: no setuid, setgroups or security mutation. */
static void context(void) {
    uid_t r,e,s; gid_t gr,ge,gs;
    struct __user_cap_header_struct hdr={_LINUX_CAPABILITY_VERSION_3,0};
    struct __user_cap_data_struct caps[2]={{0}};
    if(getresuid(&r,&e,&s)||getresgid(&gr,&ge,&gs)||r!=1000||e!=1000||s!=1000||
       gr!=1000||ge!=1000||gs!=1000||getgroups(0,NULL)!=0||
       prctl(PR_GET_NO_NEW_PRIVS,0,0,0,0)!=1||syscall(SYS_capget,&hdr,caps)) refuse();
    for(unsigned i=0;i<2;i++) if(caps[i].effective||caps[i].permitted||caps[i].inheritable) refuse();
    for(int i=0;i<=CAP_LAST_CAP;i++)
        if(prctl(PR_CAPBSET_READ,i,0,0,0)!=0||prctl(PR_CAP_AMBIENT,PR_CAP_AMBIENT_IS_SET,i,0,0)!=0) refuse();
    /* Refuse kernels exposing capabilities unknown to these build headers. */
    errno=0;
    if(prctl(PR_CAPBSET_READ,CAP_LAST_CAP+1,0,0,0)!=-1||errno!=EINVAL) refuse();
}
static void descriptors(void) {
    for(int fd=0;fd<3;fd++) {
        struct stat st;
        if(fstat(fd,&st)||S_ISSOCK(st.st_mode)) refuse();
    }
    /* Fail closed on old kernels; never leave high descriptors behind. */
    if(syscall(SYS_close_range,3U,~0U,0)) refuse();
}
static void root_file(const char *path) {
    char buf[PATH_MAX]; struct stat st; size_t len=strlen(path);
    if(len>=sizeof(buf)||path[0]!='/') refuse();
    if(lstat("/",&st)||st.st_uid!=0||(st.st_mode&0022)) refuse();
    memcpy(buf,path,len+1);
    for(size_t i=1;i<=len;i++) if(buf[i]=='/'||buf[i]=='\0') {
        char save=buf[i];buf[i]='\0';
        if(lstat(buf,&st)||st.st_uid!=0||(st.st_mode&0022)||S_ISLNK(st.st_mode)||
           (i<len&&!S_ISDIR(st.st_mode))||(i==len&&(!S_ISREG(st.st_mode)||(st.st_mode&06000)))) refuse();
        buf[i]=save;
    }
}
static void owned(const char *path, int missing) {
    char resolved[PATH_MAX],buf[PATH_MAX]; struct stat st; size_t len=strlen(path);
    if(len>=sizeof(buf)||strncmp(path,RUNTIME,strlen(RUNTIME))||strstr(path,"/../")||strstr(path,"/./")) refuse();
    memcpy(buf,path,len+1);
    if(missing&&lstat(buf,&st)&&errno==ENOENT) {
        char *slash=strrchr(buf,'/'); if(!slash||!slash[1]) refuse(); *slash='\0';
    }
    if(!realpath(buf,resolved)||strcmp(buf,resolved)) refuse();
    for(size_t i=strlen(RUNTIME)-1;i<=strlen(buf);i++) if(buf[i]=='/'||buf[i]=='\0') {
        char save=buf[i];buf[i]='\0';
        if(lstat(buf,&st)||st.st_uid!=1000||(st.st_mode&0022)||S_ISLNK(st.st_mode)) refuse();
        buf[i]=save;
    }
}
#define DENY(n) BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,(n),0,1), BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ERRNO|EPERM)
/* No pointer inspection. No UNIX socket can be created, inherited or imported.
 * TCP connect stays available; actual provider/DNS compatibility is unobserved.
 */
static struct sock_filter filter[]={
    BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,arch)),
    BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,AUDIT_ARCH_X86_64,1,0),
    BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_KILL_PROCESS),
    BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,nr)),
    BPF_JUMP(BPF_JMP|BPF_JSET|BPF_K,0x40000000,0,1),
    BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_KILL_PROCESS),
    /* Reject obsolete untagged x32 syscall numbers and unreviewed ABI growth. */
    BPF_JUMP(BPF_JMP|BPF_JGE|BPF_K,512,0,1),
    BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_KILL_PROCESS),
    DENY(SYS_socketpair), DENY(SYS_io_uring_setup), DENY(SYS_io_uring_enter), DENY(SYS_io_uring_register),
    DENY(SYS_ptrace), DENY(SYS_process_vm_readv), DENY(SYS_process_vm_writev), DENY(SYS_pidfd_getfd),
    /* /proc/PID/fd open cannot duplicate sockets; pidfd_getfd is denied above. */
    BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,SYS_socket,0,4),
    BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,args[0])),
    BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,AF_INET,2,0),
    BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,AF_INET6,1,0),
    BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ERRNO|EPERM),
    BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ALLOW)
};
int main(int argc,char **argv) {
    context(); /* MUST precede every mutation, path inspection and native exec. */
    descriptors();
    if(clearenv()) refuse();
    if(argc!=6||(strcmp(argv[1],"workspace-write")&&strcmp(argv[1],"read-only"))) refuse();
    for(int i=1;i<argc;i++) if(strlen(argv[i])>4095) refuse();
    for(int i=2;i<argc;i++) owned(argv[i],i==3||i==5);
    if(!strstr(argv[2],"/workspaces/")||!strstr(argv[3],"/attempts/")||
       !strstr(argv[4],"/attempts/")||!strstr(argv[5],"/attempts/")) refuse();
    const char *output=strrchr(argv[3],'/'),*homebase=strrchr(argv[4],'/'),*statebase=strrchr(argv[5],'/');
    if(!output||!homebase||!statebase||strcmp(output,"/final-message.txt")||
       strncmp(homebase,"/codex-home-",12)||strcmp(statebase,"/codex-state")||
       output-argv[3]!=homebase-argv[4]||output-argv[3]!=statebase-argv[5]||
       strncmp(argv[3],argv[4],(size_t)(output-argv[3]))||
       strncmp(argv[3],argv[5],(size_t)(output-argv[3]))) refuse();
    char auth[PATH_MAX],target[PATH_MAX]; struct stat st;
    if(lstat(argv[4],&st)||!S_ISDIR(st.st_mode)||(st.st_mode&0777)!=0700||
       snprintf(auth,sizeof(auth),"%s/auth.json",argv[4])>=(int)sizeof(auth)) refuse();
    ssize_t n=readlink(auth,target,sizeof(target)-1);
    if(n<0) refuse();
    target[n]='\0';
    if(strcmp(target,"/home/user/.codex/auth.json")) refuse();
    root_file(NATIVE);
    int fd=open(NATIVE,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);char hash[65];
    if(fd<0) refuse();
    hash_fd(fd,hash);close(fd);
    if(strcmp(hash,NATIVE_SHA256)) refuse();
    if(chdir(argv[2])) refuse();
    char home[PATH_MAX+16],state[PATH_MAX+24];
    snprintf(home,sizeof(home),"CODEX_HOME=%s",argv[4]);
    snprintf(state,sizeof(state),"CODEX_SQLITE_HOME=%s",argv[5]);
    char *env[]={"HOME=/home/user","USER=user","LANG=C.UTF-8","PATH=/usr/bin:/bin",home,state,
        "LANGCHAIN_TRACING_V2=false","LANGSMITH_TRACING=false","OTEL_SDK_DISABLED=true","GIT_CONFIG_COUNT=0",NULL};
    char *args[]={NATIVE,"exec","--json","--ignore-user-config","--sandbox",argv[1],"-c","approval_policy=\"never\"",
        "-c","model_reasoning_effort=\"medium\"","--model","gpt-6.1-sol","--cd",argv[2],"--output-last-message",argv[3],"-",NULL};
    struct sock_fprog program={(unsigned short)(sizeof(filter)/sizeof(filter[0])),filter};
    if(prctl(PR_SET_SECCOMP,SECCOMP_MODE_FILTER,&program)) refuse();
    execve(NATIVE,args,env);
    refuse();
}
