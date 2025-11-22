#!/usr/bin/env python3
"""
测试mitmproxy内存限制功能的脚本
"""

import sys
import os
import time
import threading
import gc

# 添加mitmproxy路径到Python路径
sys.path.insert(0, '/Users/tanfujun/brix/tt-kimi-annotation/mitmproxy')

try:
    from mitmproxy.proxy.utils import ReceiveBuffer
    from mitmproxy.proxy.layers.http import HttpStream
    from mitmproxy.proxy.context import Context
    from mitmproxy import options
    from mitmproxy.http import Headers
    from mitmproxy.connection import Client
    from mitmproxy.net.server_spec import ServerSpec
    
    print("✓ 成功导入mitmproxy模块")
    
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    sys.exit(1)

def test_receive_buffer_memory_limits():
    """测试ReceiveBuffer的内存限制功能"""
    print("\n=== 测试ReceiveBuffer内存限制 ===")
    
    # 测试1: 正常添加数据
    buf = ReceiveBuffer(max_size=1024)  # 1KB限制
    try:
        buf += b"A" * 500  # 500字节，应该成功
        print(f"✓ 正常添加500字节数据，当前大小: {buf._len}字节")
        
        # 测试内存使用统计
        memory_usage = buf.get_memory_usage()
        print(f"✓ 内存使用量: {memory_usage}字节")
        
    except Exception as e:
        print(f"✗ 正常添加数据失败: {e}")
        return False
    
    # 测试2: 超出内存限制
    try:
        buf += b"B" * 600  # 再添加600字节，应该超出1KB限制
        print(f"✗ 应该触发内存限制异常，但没有触发")
        return False
    except MemoryError as e:
        print(f"✓ 正确触发内存限制异常: {e}")
    except Exception as e:
        print(f"✗ 意外的异常: {e}")
        return False
    
    # 测试3: 清理策略
    try:
        buf.clear()
        print(f"✓ 清理缓冲区后大小: {buf._len}字节")
        
        # 重新添加数据
        buf += b"C" * 300
        print(f"✓ 重新添加300字节数据，当前大小: {buf._len}字节")
        
        # 测试部分清理
        cleared = buf.clear_oldest(100)
        print(f"✓ 部分清理后大小: {buf._len}字节，清理数据大小: {len(cleared)}字节")
        
        # 测试压缩
        buf.compact()
        print(f"✓ 压缩后chunks数量: {len(buf._chunks)}")
        
    except Exception as e:
        print(f"✗ 清理策略测试失败: {e}")
        return False
    
    return True

def test_http_stream_memory_tracking():
    """测试HttpStream的内存跟踪功能"""
    print("\n=== 测试HttpStream内存跟踪 ===")
    
    try:
        # 创建模拟的context和options
        opts = options.Options()
        opts.body_buffer_limit = "2k"  # 2KB限制
        
        client = Client(("127.0.0.1", 8080), ("127.0.0.1", 8080), "tcp", "http")
        context = Context(client, opts)
        
        # 创建HttpStream实例
        stream = HttpStream(context, 1)
        print(f"✓ 创建HttpStream实例，流ID: {stream.stream_id}")
        
        # 测试内存统计
        stats = stream.get_memory_stats()
        print(f"✓ 初始内存统计: {stats}")
        
        # 模拟添加数据到缓冲区
        stream.response_body_buf += b"X" * 1000  # 1KB响应数据
        stream.request_body_buf += b"Y" * 800   # 800字节请求数据
        
        # 更新内存统计
        stream._update_memory_stats()
        stats = stream.get_memory_stats()
        print(f"✓ 添加数据后内存统计:")
        print(f"  - 当前内存使用: {stats['current_memory']}字节")
        print(f"  - 峰值内存使用: {stats['peak_memory']}字节")
        print(f"  - 响应缓冲区大小: {stats['response_buffer_size']}字节")
        print(f"  - 请求缓冲区大小: {stats['request_buffer_size']}字节")
        
        # 测试内存限制检查
        is_over_limit = stream._check_memory_limits()
        print(f"✓ 内存限制检查: {'超出限制' if is_over_limit else '正常'}")
        
        # 测试清理功能
        stream._cleanup_buffers()
        stats_after = stream.get_memory_stats()
        print(f"✓ 清理后内存统计:")
        print(f"  - 当前内存使用: {stats_after['current_memory']}字节")
        print(f"  - 响应缓冲区大小: {stats_after['response_buffer_size']}字节")
        print(f"  - 请求缓冲区大小: {stats_after['request_buffer_size']}字节")
        
    except Exception as e:
        print(f"✗ HttpStream内存跟踪测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_size_parsing():
    """测试大小解析功能"""
    print("\n=== 测试大小解析功能 ===")
    
    try:
        # 创建临时HttpStream来测试私有方法
        opts = options.Options()
        client = Client(("127.0.0.1", 8080), ("127.0.0.1", 8080), "tcp", "http")
        context = Context(client, opts)
        stream = HttpStream(context, 1)
        
        # 测试各种格式的大小解析
        test_cases = [
            ("1k", 1024),
            ("2K", 2048),
            ("1m", 1024*1024),
            ("512M", 512*1024*1024),
            ("1g", 1024*1024*1024),
            ("1024", 1024),  # 纯数字
            ("invalid", 1024*1024),  # 无效格式，应该返回默认值
        ]
        
        for size_str, expected in test_cases:
            result = stream._parse_size(size_str)
            if result == expected:
                print(f"✓ '{size_str}' -> {result}字节 (正确)")
            else:
                print(f"✗ '{size_str}' -> {result}字节 (期望: {expected})")
                return False
        
    except Exception as e:
        print(f"✗ 大小解析测试失败: {e}")
        return False
    
    return True

def main():
    """主测试函数"""
    print("开始测试mitmproxy内存限制功能...")
    
    tests = [
        test_receive_buffer_memory_limits,
        test_http_stream_memory_tracking,
        test_size_parsing,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
                print(f"✓ {test.__name__} 通过")
            else:
                print(f"✗ {test.__name__} 失败")
        except Exception as e:
            print(f"✗ {test.__name__} 异常: {e}")
    
    print(f"\n=== 测试结果 ===")
    print(f"通过: {passed}/{total}")
    print(f"失败: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("❌ 部分测试失败")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)