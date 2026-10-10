"""Read Windows process resources for pinned roots; no process mutation or extra packages."""
import ctypes
import os
import shutil
import time
from datetime import datetime, timezone


def descendants(records, root):
    """Select a process forest by parent PID, including the root itself."""
    if type(root) is not int or root < 1 or root not in records:
        raise RuntimeError('La raíz del árbol no está presente')
    selected = {root}
    while True:
        expanded = selected | {pid for pid, item in records.items()
                               if item['parent_pid'] in selected}
        if expanded == selected:
            return selected
        selected = expanded


def validate_tree(records, measured, root):
    """Reject missing readings, reused root IDs and children older than their parent."""
    selected = descendants(records, root['pid'])
    if set(measured) != selected or any(not item.get('available') for item in measured.values()):
        raise RuntimeError('Faltan lecturas del árbol de procesos')
    if measured[root['pid']]['stamp'] != root['stamp']:
        raise RuntimeError('La identidad de la raíz cambió')
    for pid in selected - {root['pid']}:
        parent = records[pid]['parent_pid']
        if int(measured[pid]['stamp']) < int(measured[parent]['stamp']):
            raise RuntimeError('La ascendencia contiene un PID reutilizado')
    return [dict(measured[pid], parent_pid=records[pid]['parent_pid'],
                 name=records[pid]['name']) for pid in sorted(selected)]


def qualified_tree(records, measured, root):
    """Remove stale parent-PID links and their branches before attributing resources."""
    selected = descendants(records, root['pid'])
    if set(measured) != selected or any(not r.get('available') for r in measured.values()):
        raise RuntimeError('Faltan lecturas del árbol de procesos')
    if measured[root['pid']]['stamp'] != root['stamp']:
        raise RuntimeError('La identidad de la raíz cambió')
    filtered = dict(records)
    links = []
    for pid in selected - {root['pid']}:
        parent = records[pid]['parent_pid']
        if int(measured[pid]['stamp']) < int(measured[parent]['stamp']):
            links.append({'pid': pid, 'parent_pid': parent,
                          'stamp': measured[pid]['stamp'], 'parent_stamp': measured[parent]['stamp']})
            filtered[pid] = dict(records[pid], parent_pid=0)
    accepted = descendants(filtered, root['pid'])
    result = validate_tree(filtered, {pid: measured[pid] for pid in accepted}, root)
    return result, {'parent_links': sorted(links, key=lambda r: r['pid']),
                    'excluded_pids': sorted(selected - accepted)}


class ProcessEntry(ctypes.Structure):
    _fields_ = [('size', ctypes.c_ulong), ('usage', ctypes.c_ulong), ('pid', ctypes.c_ulong),
                ('heap', ctypes.c_size_t), ('module', ctypes.c_ulong), ('threads', ctypes.c_ulong),
                ('parent', ctypes.c_ulong), ('priority', ctypes.c_long), ('flags', ctypes.c_ulong),
                ('name', ctypes.c_wchar * 260)]


class MemoryCounters(ctypes.Structure):
    _fields_ = [('size', ctypes.c_ulong), ('faults', ctypes.c_ulong)] + [
        (name, ctypes.c_size_t) for name in ('peak_ws', 'ws', 'peak_paged', 'paged',
        'peak_nonpaged', 'nonpaged', 'pagefile', 'peak_pagefile', 'private')]


class SystemMemory(ctypes.Structure):
    _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [
        (name, ctypes.c_ulonglong) for name in ('total_phys', 'available_phys', 'total_page',
        'available_page', 'total_virtual', 'available_virtual', 'available_extended')]


class IOCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in
               ('read_operations', 'write_operations', 'other_operations',
                'read_bytes', 'write_bytes', 'other_bytes')]


class WindowsObserver:
    def sample_with_retries(self, roots, directory, max_attempts=3):
        """Discard explicitly recorded churn, retry briefly, and fail if no stable sample exists."""
        if type(max_attempts) is not int or not 1 <= max_attempts <= 8:
            raise ValueError('El máximo debe estar entre uno y ocho intentos')
        started = time.monotonic()
        discarded = []
        for attempt in range(max_attempts):
            try:
                result = self.sample(roots, directory)
                result['sampling_attempts'] = attempt + 1
                result['discarded_attempts'] = discarded
                result['collection_seconds_including_retries'] = time.monotonic() - started
                return result
            except RuntimeError as exc:
                if str(exc) not in ('Faltan lecturas del árbol de procesos',
                                    'El árbol cambió durante la muestra; no se acredita cobertura'):
                    raise
                discarded.append({'reason': str(exc), 'at_utc': datetime.now(timezone.utc).isoformat()})
                if attempt + 1 == max_attempts:
                    raise
                time.sleep(0.05)

    def __init__(self):
        if os.name != 'nt':
            raise RuntimeError('Este observador requiere Windows')
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.psapi = ctypes.WinDLL('psapi', use_last_error=True)
        kernel = self.kernel
        kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.CreateToolhelp32Snapshot.argtypes = [ctypes.c_ulong, ctypes.c_ulong]
        kernel.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
        kernel.Process32FirstW.argtypes = kernel.Process32NextW.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(ProcessEntry)]
        kernel.GetProcessTimes.argtypes = [ctypes.c_void_p] + [ctypes.c_void_p] * 4
        kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        kernel.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_ulong,
                                                     ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]
        kernel.GetProcessIoCounters.argtypes = [ctypes.c_void_p, ctypes.POINTER(IOCounters)]
        kernel.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(SystemMemory)]
        self.psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(MemoryCounters), ctypes.c_ulong]

    def inventory(self):
        handle = self.kernel.CreateToolhelp32Snapshot(2, 0)
        if handle in (None, ctypes.c_void_p(-1).value):
            raise RuntimeError('No se pudo enumerar los procesos')
        records = {}
        try:
            entry = ProcessEntry(); entry.size = ctypes.sizeof(entry)
            present = self.kernel.Process32FirstW(handle, ctypes.byref(entry))
            if not present:
                raise RuntimeError('El inventario de procesos está vacío')
            while present:
                records[int(entry.pid)] = {'parent_pid': int(entry.parent), 'name': entry.name}
                present = self.kernel.Process32NextW(handle, ctypes.byref(entry))
        finally:
            self.kernel.CloseHandle(handle)
        return records

    def process(self, pid):
        if type(pid) is not int or pid < 1:
            return {'pid': pid, 'available': False}
        handle = self.kernel.OpenProcess(0x1010, False, pid)
        if not handle:
            return {'pid': pid, 'available': False}
        try:
            times = [(ctypes.c_ulong * 2)() for _ in range(4)]
            counters = MemoryCounters(); counters.size = ctypes.sizeof(counters)
            io = IOCounters(); image = ctypes.create_unicode_buffer(32768)
            size = ctypes.c_ulong(len(image)); exit_code = ctypes.c_ulong()
            if not (self.kernel.GetProcessTimes(handle, *(ctypes.byref(value) for value in times))
                    and self.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.size)
                    and self.kernel.GetProcessIoCounters(handle, ctypes.byref(io))
                    and self.kernel.QueryFullProcessImageNameW(handle, 0, image, ctypes.byref(size))
                    and self.kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                    and exit_code.value == 259):
                return {'pid': pid, 'available': False}
            integer = lambda value: int(value[0]) | (int(value[1]) << 32)
            return {'pid': pid, 'available': True, 'stamp': str(integer(times[0])),
                    'image': image.value, 'private_bytes': int(counters.private),
                    'working_set_bytes': int(counters.ws),
                    'cpu_seconds': (integer(times[2]) + integer(times[3])) / 10_000_000,
                    'io_read_bytes': int(io.read_bytes), 'io_write_bytes': int(io.write_bytes)}
        finally:
            self.kernel.CloseHandle(handle)

    def sample(self, roots, directory):
        started = time.monotonic()
        records = self.inventory()
        groups = {}
        exclusions = {}
        for name, root in roots.items():
            selected = descendants(records, root['pid'])
            measured = {pid: self.process(pid) for pid in selected}
            groups[name], exclusions[name] = qualified_tree(records, measured, root)
        # Detect churn/reused IDs during collection instead of silently undercounting.
        after = self.inventory()
        for name, root in roots.items():
            selected = descendants(after, root['pid'])
            actual = {pid: self.process(pid) for pid in selected}
            verified, excluded_after = qualified_tree(after, actual, root)
            if {(r['pid'], r['stamp'], r['parent_pid']) for r in verified} != {
                    (r['pid'], r['stamp'], r['parent_pid']) for r in groups[name]}:
                raise RuntimeError('El árbol cambió durante la muestra; no se acredita cobertura')
            exclusions[name]['second_inventory'] = excluded_after
        memory = SystemMemory(); memory.length = ctypes.sizeof(memory)
        if not self.kernel.GlobalMemoryStatusEx(ctypes.byref(memory)):
            raise RuntimeError('No se pudo medir la memoria física')
        return {'at_utc': datetime.now(timezone.utc).isoformat(),
                'monotonic_seconds': started, 'collection_seconds': time.monotonic() - started,
                'groups': groups, 'available_physical_bytes': int(memory.available_phys),
                'excluded_stale_parent_links': exclusions,
                'free_disk_bytes': shutil.disk_usage(directory).free,
                'process_inventory_stable': True}
