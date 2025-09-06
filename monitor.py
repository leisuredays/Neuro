#!/usr/bin/env python3
"""
System Monitor - 스레드, 메모리, 성능 모니터링
"""

import threading
import psutil
import time
import gc
import os
from typing import Dict, List, Any
from datetime import datetime


class SystemMonitor:
    """시스템 리소스 및 스레드 모니터링 클래스"""
    
    def __init__(self, signals=None, interval: float = 5.0):
        self.signals = signals
        self.interval = interval
        self.process = psutil.Process()
        self.start_time = time.time()
        self.is_running = False
        self.monitor_thread = None
        
        # 통계 데이터
        self.stats = {
            "peak_memory_mb": 0,
            "peak_thread_count": 0,
            "total_gc_collections": 0,
            "average_cpu_percent": 0.0,
            "uptime_seconds": 0
        }
        
        # 히스토리 (최근 60개 데이터포인트)
        self.history = {
            "timestamps": [],
            "memory_usage": [],
            "thread_counts": [],
            "cpu_usage": []
        }
    
    def start_monitoring(self):
        """모니터링 시작"""
        if self.is_running:
            print("[MONITOR] Already running")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        print("[MONITOR] Started system monitoring")
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.is_running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        print("[MONITOR] Stopped system monitoring")
    
    def _monitoring_loop(self):
        """모니터링 메인 루프"""
        while self.is_running:
            try:
                self._collect_metrics()
                time.sleep(self.interval)
            except Exception as e:
                print(f"[MONITOR] Error in monitoring loop: {e}")
                time.sleep(1.0)
    
    def _collect_metrics(self):
        """메트릭 수집"""
        current_time = time.time()
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 메모리 사용량
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        # CPU 사용률
        cpu_percent = self.process.cpu_percent()
        
        # 스레드 정보
        thread_count = self.process.num_threads()
        active_threads = threading.enumerate()
        
        # 통계 업데이트
        self.stats["peak_memory_mb"] = max(self.stats["peak_memory_mb"], memory_mb)
        self.stats["peak_thread_count"] = max(self.stats["peak_thread_count"], thread_count)
        self.stats["uptime_seconds"] = current_time - self.start_time
        
        # 히스토리 업데이트 (최근 60개만 유지)
        self.history["timestamps"].append(timestamp)
        self.history["memory_usage"].append(memory_mb)
        self.history["thread_counts"].append(thread_count)
        self.history["cpu_usage"].append(cpu_percent)
        
        # 최근 60개 데이터만 유지
        for key in self.history:
            if len(self.history[key]) > 60:
                self.history[key] = self.history[key][-60:]
        
        # 콘솔 출력 (5분마다)
        if int(current_time) % 300 == 0:  # 5분마다
            self._print_status()
    
    def _print_status(self):
        """현재 상태 출력"""
        memory_mb = self.history["memory_usage"][-1] if self.history["memory_usage"] else 0
        thread_count = self.history["thread_counts"][-1] if self.history["thread_counts"] else 0
        cpu_percent = self.history["cpu_usage"][-1] if self.history["cpu_usage"] else 0
        
        print(f"\n[MONITOR] === System Status ===")
        print(f"[MONITOR] Memory: {memory_mb:.1f} MB (Peak: {self.stats['peak_memory_mb']:.1f} MB)")
        print(f"[MONITOR] Threads: {thread_count} (Peak: {self.stats['peak_thread_count']})")
        print(f"[MONITOR] CPU: {cpu_percent:.1f}%")
        print(f"[MONITOR] Uptime: {self.stats['uptime_seconds']/3600:.1f} hours")
    
    def get_detailed_thread_info(self) -> List[Dict[str, Any]]:
        """상세 스레드 정보 조회"""
        threads = []
        for thread in threading.enumerate():
            thread_info = {
                "name": thread.name,
                "ident": thread.ident,
                "is_alive": thread.is_alive(),
                "daemon": thread.daemon,
                "is_main": thread == threading.main_thread()
            }
            threads.append(thread_info)
        
        return threads
    
    def get_memory_breakdown(self) -> Dict[str, float]:
        """메모리 사용량 세부 정보"""
        memory_info = self.process.memory_info()
        
        return {
            "rss_mb": memory_info.rss / 1024 / 1024,  # 실제 메모리
            "vms_mb": memory_info.vms / 1024 / 1024,  # 가상 메모리
            "percent": self.process.memory_percent(),
            "available_system_mb": psutil.virtual_memory().available / 1024 / 1024
        }
    
    def force_garbage_collection(self) -> Dict[str, int]:
        """가비지 컬렉션 강제 실행"""
        print("[MONITOR] Running garbage collection...")
        
        collected = {
            "generation_0": gc.collect(0),
            "generation_1": gc.collect(1), 
            "generation_2": gc.collect(2)
        }
        
        total_collected = sum(collected.values())
        self.stats["total_gc_collections"] += total_collected
        
        print(f"[MONITOR] Collected {total_collected} objects")
        return collected
    
    def get_system_summary(self) -> Dict[str, Any]:
        """시스템 요약 정보"""
        threads = self.get_detailed_thread_info()
        memory = self.get_memory_breakdown()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "uptime_hours": self.stats["uptime_seconds"] / 3600,
            "memory": memory,
            "threads": {
                "active_count": len(threads),
                "peak_count": self.stats["peak_thread_count"],
                "details": threads
            },
            "performance": {
                "peak_memory_mb": self.stats["peak_memory_mb"],
                "total_gc_collections": self.stats["total_gc_collections"],
                "cpu_percent": self.process.cpu_percent()
            },
            "recent_history": {
                "memory_trend": self.history["memory_usage"][-10:],
                "thread_trend": self.history["thread_counts"][-10:],
                "cpu_trend": self.history["cpu_usage"][-10:]
            }
        }
    
    def print_detailed_report(self):
        """상세 보고서 출력"""
        summary = self.get_system_summary()
        
        print(f"\n{'='*60}")
        print(f"[MONITOR] DETAILED SYSTEM REPORT")
        print(f"{'='*60}")
        print(f"Timestamp: {summary['timestamp']}")
        print(f"Uptime: {summary['uptime_hours']:.2f} hours")
        
        print(f"\n--- MEMORY ---")
        mem = summary['memory']
        print(f"Current Usage: {mem['rss_mb']:.1f} MB ({mem['percent']:.1f}%)")
        print(f"Peak Usage: {summary['performance']['peak_memory_mb']:.1f} MB")
        print(f"Virtual Memory: {mem['vms_mb']:.1f} MB")
        print(f"System Available: {mem['available_system_mb']:.1f} MB")
        
        print(f"\n--- THREADS ---")
        thread_info = summary['threads']
        print(f"Active Threads: {thread_info['active_count']}")
        print(f"Peak Threads: {thread_info['peak_count']}")
        
        print(f"\nThread Details:")
        for thread in thread_info['details']:
            status = "ALIVE" if thread['is_alive'] else "DEAD"
            daemon = "DAEMON" if thread['daemon'] else "NORMAL"
            main = " (MAIN)" if thread['is_main'] else ""
            print(f"  - {thread['name']}: {status} | {daemon}{main}")
        
        print(f"\n--- PERFORMANCE ---")
        perf = summary['performance']
        print(f"Current CPU: {perf['cpu_percent']:.1f}%")
        print(f"GC Collections: {perf['total_gc_collections']}")
        
        print(f"\n--- RECENT TRENDS (Last 10 samples) ---")
        history = summary['recent_history']
        print(f"Memory: {' → '.join([f'{x:.0f}' for x in history['memory_trend']])}")
        print(f"Threads: {' → '.join([str(x) for x in history['thread_trend']])}")
        print(f"CPU: {' → '.join([f'{x:.0f}%' for x in history['cpu_usage']])}")
        print(f"{'='*60}\n")


# 전역 모니터 인스턴스
_global_monitor = None

def get_system_monitor() -> SystemMonitor:
    """전역 시스템 모니터 인스턴스 가져오기"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = SystemMonitor()
    return _global_monitor

def start_monitoring(signals=None, interval: float = 5.0):
    """모니터링 시작"""
    monitor = get_system_monitor()
    monitor.signals = signals
    monitor.interval = interval
    monitor.start_monitoring()

def stop_monitoring():
    """모니터링 중지"""
    monitor = get_system_monitor()
    monitor.stop_monitoring()

def print_status():
    """현재 상태 출력"""
    monitor = get_system_monitor()
    monitor._print_status()

def print_report():
    """상세 보고서 출력"""
    monitor = get_system_monitor()
    monitor.print_detailed_report()

def cleanup_system():
    """시스템 정리"""
    monitor = get_system_monitor()
    collected = monitor.force_garbage_collection()
    print(f"[MONITOR] System cleanup completed: {sum(collected.values())} objects collected")

def interactive_monitor():
    """심플 인터랙티브 모니터링 모드"""
    print("🔍 Real-time System Monitor")
    print("매 2초마다 자동 업데이트됩니다. Ctrl+C로 종료하세요.")
    print("-" * 60)
    
    monitor = SystemMonitor(interval=2.0)  # 2초마다 업데이트
    monitor.start_monitoring()
    
    try:
        counter = 0
        while True:
            counter += 1
            
            # 실시간 상태 표시
            if monitor.history["memory_usage"]:
                memory = monitor.history["memory_usage"][-1]
                threads = monitor.history["thread_counts"][-1] 
                cpu = monitor.history["cpu_usage"][-1]
                timestamp = monitor.history["timestamps"][-1]
                
                print(f"[{timestamp}] Memory: {memory:6.1f}MB | Threads: {threads:2d} | CPU: {cpu:5.1f}% | Update #{counter}")
                
                # 매 10회마다 상세 정보 출력
                if counter % 10 == 0:
                    print("-" * 60)
                    monitor._print_status()
                    print("-" * 60)
                
                # 매 30회마다 가비지 컬렉션
                if counter % 30 == 0:
                    collected = monitor.force_garbage_collection()
                    print(f"🧹 Auto cleanup: {sum(collected.values())} objects collected")
                    print("-" * 60)
            
            time.sleep(2.0)
            
    except KeyboardInterrupt:
        print("\n\nStopping monitor...")
        monitor.print_detailed_report()  # 종료 전 마지막 리포트
    finally:
        monitor.stop_monitoring()
        print("Monitor stopped.")


def dashboard_monitor():
    """대시보드 스타일 모니터링"""
    import os
    
    monitor = SystemMonitor(interval=2.0)
    monitor.start_monitoring()
    
    try:
        while True:
            # 화면 지우기
            os.system('cls' if os.name == 'nt' else 'clear')
            
            # 헤더
            print("🖥️  SYSTEM MONITOR DASHBOARD")
            print("=" * 60)
            print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Uptime: {monitor.stats['uptime_seconds']/3600:.2f} hours")
            print()
            
            # 현재 상태
            if monitor.history["memory_usage"]:
                memory = monitor.history["memory_usage"][-1]
                threads = monitor.history["thread_counts"][-1]
                cpu = monitor.history["cpu_usage"][-1]
                
                # 시스템 총 메모리 정보
                total_memory_mb = psutil.virtual_memory().total / 1024 / 1024
                
                # 메모리 바 (시스템 총 메모리 대비)
                memory_bar = create_ascii_bar(memory, total_memory_mb, 30)
                print(f"💾 Memory:  {memory:6.1f} MB {memory_bar} / {total_memory_mb:.0f}MB")
                
                # 스레드 바 (일반적인 최대 스레드 수 기준: 50개)
                thread_bar = create_ascii_bar(threads, 50, 30)
                print(f"🧵 Threads: {threads:6d}    {thread_bar} Peak: {monitor.stats['peak_thread_count']}")
                
                # CPU 바
                cpu_bar = create_ascii_bar(cpu, 100, 30)
                print(f"⚡ CPU:     {cpu:6.1f} %  {cpu_bar}")
                
                print()
                
                # 트렌드 (최근 10개)
                if len(monitor.history["memory_usage"]) >= 10:
                    print("📈 Memory Trend (MB):")
                    memory_trend = monitor.history["memory_usage"][-10:]
                    print("   " + " ".join([f"{x:4.0f}" for x in memory_trend]))
                    
                    print("📊 Thread Trend:")
                    thread_trend = monitor.history["thread_counts"][-10:]
                    print("   " + " ".join([f"{x:4d}" for x in thread_trend]))
                    
                    print("🔥 CPU Trend (%):")
                    cpu_trend = monitor.history["cpu_usage"][-10:]
                    print("   " + " ".join([f"{x:4.0f}" for x in cpu_trend]))
            
            print()
            print("=" * 60)
            print("Press Ctrl+C to exit")
            
            time.sleep(2.0)
            
    except KeyboardInterrupt:
        print("\n\nStopping dashboard...")
    finally:
        monitor.stop_monitoring()
        print("Dashboard stopped.")


def create_ascii_bar(value: float, max_value: float, width: int = 30) -> str:
    """ASCII 진행률 바 생성"""
    if max_value == 0:
        percentage = 0
    else:
        percentage = min(value / max_value, 1.0)
    
    filled = int(percentage * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {percentage*100:5.1f}%"


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="System Monitor - 스레드 및 메모리 모니터링")
    parser.add_argument("--mode", "-m", choices=["interactive", "dashboard", "test"], 
                       default="interactive", help="모니터링 모드 선택")
    parser.add_argument("--interval", "-i", type=float, default=1.0, 
                       help="모니터링 간격 (초)")
    
    args = parser.parse_args()
    
    if args.mode == "interactive":
        interactive_monitor()
    elif args.mode == "dashboard":
        dashboard_monitor()
    elif args.mode == "test":
        # 기존 테스트 코드
        print("Starting system monitor test...")
        
        monitor = SystemMonitor(interval=args.interval)
        monitor.start_monitoring()
        
        try:
            # 10초 동안 실행
            time.sleep(10)
            monitor.print_detailed_report()
            
            # 가비지 컬렉션 테스트
            monitor.force_garbage_collection()
            
        except KeyboardInterrupt:
            print("\nStopping monitor...")
        finally:
            monitor.stop_monitoring()