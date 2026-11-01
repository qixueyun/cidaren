"""Own only the runner launched by this panel and its descendants."""
import ctypes as C
from ctypes import wintypes as W

class IO(C.Structure):
    _fields_=[(name,C.c_ulonglong) for name in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]
class Basic(C.Structure):
    _fields_=[('process_time',C.c_longlong),('job_time',C.c_longlong),('flags',W.DWORD),
              ('min_working',C.c_size_t),('max_working',C.c_size_t),('active',W.DWORD),
              ('affinity',C.c_size_t),('priority',W.DWORD),('scheduling',W.DWORD)]
class Extended(C.Structure):
    _fields_=[('basic',Basic),('io',IO),('process_memory',C.c_size_t),('job_memory',C.c_size_t),
              ('peak_process',C.c_size_t),('peak_job',C.c_size_t)]

class ProcessJob:
    def __init__(self,process):
        self.k=C.WinDLL('kernel32',use_last_error=True)
        for name,args,result in [
            ('CreateJobObjectW',[C.c_void_p,W.LPCWSTR],W.HANDLE),
            ('SetInformationJobObject',[W.HANDLE,C.c_int,C.c_void_p,W.DWORD],W.BOOL),
            ('AssignProcessToJobObject',[W.HANDLE,W.HANDLE],W.BOOL),
            ('TerminateJobObject',[W.HANDLE,W.UINT],W.BOOL),
            ('CloseHandle',[W.HANDLE],W.BOOL)]:
            f=getattr(self.k,name);f.argtypes=args;f.restype=result
        self.handle=self.k.CreateJobObjectW(None,None)
        if not self.handle:raise C.WinError(C.get_last_error())
        info=Extended();info.basic.flags=0x2000
        if not self.k.SetInformationJobObject(self.handle,9,C.byref(info),C.sizeof(info)):
            error=C.WinError(C.get_last_error());self.close();raise error
        if not self.k.AssignProcessToJobObject(self.handle,W.HANDLE(int(process._handle))):
            error=C.WinError(C.get_last_error());self.close();raise error
    def terminate(self):
        if self.handle and not self.k.TerminateJobObject(self.handle,0):raise C.WinError(C.get_last_error())
    def close(self):
        if self.handle:self.k.CloseHandle(self.handle);self.handle=None
