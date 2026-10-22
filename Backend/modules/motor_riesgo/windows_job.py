"""An owned Windows job closes its analytic process tree with the API.

The child starts suspended: assigning a running venv launcher has a race in
which its real Python descendant can escape before the job is attached.
No breakaway or inheritable job handle is enabled.
"""
import ctypes
from ctypes import wintypes

CREATE_SUSPENDED=0x00000004


class BasicLimits(ctypes.Structure):
    _fields_=[('process_time',ctypes.c_longlong),('job_time',ctypes.c_longlong),
              ('flags',wintypes.DWORD),('minimum_working_set',ctypes.c_size_t),
              ('maximum_working_set',ctypes.c_size_t),('active_processes',wintypes.DWORD),
              ('affinity',ctypes.c_size_t),('priority',wintypes.DWORD),('scheduling',wintypes.DWORD)]


class IoCounters(ctypes.Structure):
    _fields_=[(name,ctypes.c_ulonglong) for name in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]


class ExtendedLimits(ctypes.Structure):
    _fields_=[('basic',BasicLimits),('io',IoCounters),('process_memory',ctypes.c_size_t),
              ('job_memory',ctypes.c_size_t),('peak_process_memory',ctypes.c_size_t),('peak_job_memory',ctypes.c_size_t)]


class ThreadEntry(ctypes.Structure):
    _fields_=[('size',wintypes.DWORD),('usage',wintypes.DWORD),('thread_id',wintypes.DWORD),
              ('owner_pid',wintypes.DWORD),('base_priority',wintypes.LONG),('delta_priority',wintypes.LONG),
              ('flags',wintypes.DWORD)]


class WindowsJob:
    def __init__(self):
        self.handle=None
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        specifications={
            'CreateJobObjectW':([ctypes.c_void_p,wintypes.LPCWSTR],wintypes.HANDLE),
            'SetInformationJobObject':([wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD],wintypes.BOOL),
            'AssignProcessToJobObject':([wintypes.HANDLE,wintypes.HANDLE],wintypes.BOOL),
            'TerminateJobObject':([wintypes.HANDLE,wintypes.UINT],wintypes.BOOL),
            'CloseHandle':([wintypes.HANDLE],wintypes.BOOL),
            'CreateToolhelp32Snapshot':([wintypes.DWORD,wintypes.DWORD],wintypes.HANDLE),
            'Thread32First':([wintypes.HANDLE,ctypes.POINTER(ThreadEntry)],wintypes.BOOL),
            'Thread32Next':([wintypes.HANDLE,ctypes.POINTER(ThreadEntry)],wintypes.BOOL),
            'OpenThread':([wintypes.DWORD,wintypes.BOOL,wintypes.DWORD],wintypes.HANDLE),
            'ResumeThread':([wintypes.HANDLE],wintypes.DWORD),
        }
        for name,(args,result) in specifications.items():
            function=getattr(self.kernel,name);function.argtypes=args;function.restype=result
        self.handle=self.kernel.CreateJobObjectW(None,None)
        if not self.handle:raise ctypes.WinError(ctypes.get_last_error())
        limits=ExtendedLimits();limits.basic.flags=0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.kernel.SetInformationJobObject(self.handle,9,ctypes.byref(limits),ctypes.sizeof(limits)):
            error=ctypes.WinError(ctypes.get_last_error());self.close();raise error

    def assign_and_resume(self,process):
        # _handle is the CPython Windows Popen handle, not a PID that could
        # identify another process after reuse. The child is still suspended.
        if not self.kernel.AssignProcessToJobObject(self.handle,int(process._handle)):
            raise ctypes.WinError(ctypes.get_last_error())
        snapshot=self.kernel.CreateToolhelp32Snapshot(0x4,0)  # TH32CS_SNAPTHREAD
        if snapshot in (None,ctypes.c_void_p(-1).value):raise ctypes.WinError(ctypes.get_last_error())
        threads=[]
        try:
            entry=ThreadEntry();entry.size=ctypes.sizeof(entry)
            more=self.kernel.Thread32First(snapshot,ctypes.byref(entry))
            if not more:raise ctypes.WinError(ctypes.get_last_error())
            while more:
                if entry.owner_pid==process.pid:threads.append(entry.thread_id)
                entry.size=ctypes.sizeof(entry)
                more=self.kernel.Thread32Next(snapshot,ctypes.byref(entry))
            if ctypes.get_last_error()!=18:raise ctypes.WinError(ctypes.get_last_error())  # ERROR_NO_MORE_FILES
        finally:self.kernel.CloseHandle(snapshot)
        if len(threads)!=1:raise RuntimeError('No se identificó un único hilo inicial suspendido')
        thread=self.kernel.OpenThread(0x2,False,threads[0])  # THREAD_SUSPEND_RESUME
        if not thread:raise ctypes.WinError(ctypes.get_last_error())
        try:
            previous=self.kernel.ResumeThread(thread)
            if previous==0xffffffff:raise ctypes.WinError(ctypes.get_last_error())
            if previous!=1:raise RuntimeError('Estado inesperado del hilo analítico suspendido')
        finally:self.kernel.CloseHandle(thread)

    def terminate(self):
        if not self.kernel.TerminateJobObject(self.handle,1):raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        if self.handle:
            handle,self.handle=self.handle,None
            if not self.kernel.CloseHandle(handle):raise ctypes.WinError(ctypes.get_last_error())
