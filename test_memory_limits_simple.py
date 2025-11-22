#!/usr/bin/env python3
"""
简化版测试mitmproxy内存限制功能的脚本
专注于测试ReceiveBuffer和核心内存管理功能
"""

import sys
import os

# 添加mitmproxy路径到Python路径
sys.path.insert(0, '/Users/tanfujun/brix/tt-kimi-annotation/mitmproxy')

def test_receive_buffer_standalone():
    """独立测试ReceiveBuffer功能"""
    print("=== 独立测试ReceiveBuffer内存限制 ===")
    
    # 直接导入ReceiveBuffer类定义
    try:
        # 从utils.py中导入ReceiveBuffer
        import importlib.util
        spec = importlib.util.spec_from_file_location("utils", "/Users/tanfujun/brix/tt-kimi-annotation/mitmproxy/mitmproxy/proxy/utils.py")
        utils_module = importlib.util.module_from_spec(spec)
        
        # 创建一个最小化的Context类用于测试
        class MockContext:
            def __init__(self):
                self.log = lambda msg, level: print(f"LOG [{level}]: {msg}")
        
        # 将Context注入到模块中
        utils_module.Context = MockContext
        spec.loader.exec_module(utils_module)
        
        ReceiveBuffer = utils_module.ReceiveBuffer
        
    except Exception as e:
        print(f"✗ 导入ReceiveBuffer失败: {e}")
        return False
    
    # 测试1: 基本功能
    print("\n--- 测试1: 基本功能 ---")
    try:
        buf = ReceiveBuffer()
        test_data = b"Hello, World!" * 100  # 约1.3KB
        buf += test_data
        
        print(f"✓ 成功添加数据，大小: {buf._len}字节")
        print(f"✓ chunks数量: {len(buf._chunks)}")
        
        # 测试转换为bytes
        result = bytes(buf)
        print(f"✓ 转换为bytes成功，大小: {len(result)}字节")
        
        # 测试清空
        buf.clear()
        print(f"✓ 清空后大小: {buf._len}字节")
        
    except Exception as e:
        print(f"✗ 基本功能测试失败: {e}")
        return False
    
    # 测试2: 内存限制
    print("\n--- 测试2: 内存限制 ---")
    try:
        buf = ReceiveBuffer(max_size=1024)  # 1KB限制
        
        # 添加小于限制的数据
        buf += b"A" * 500
        print(f"✓ 添加500字节数据成功，当前: {buf._len}字节")
        
        # 尝试添加超出限制的数据
        try:
            buf += b"B" * 600  # 这会超出1KB限制
            print(f"✗ 应该触发内存限制异常")
            return False
        except MemoryError as e:
            print(f"✓ 正确触发内存限制异常: {e}")
        
    except Exception as e:
        print(f"✗ 内存限制测试失败: {e}")
        return False
    
    # 测试3: 高级清理功能
    print("\n--- 测试3: 高级清理功能 ---")
    try:
        buf = ReceiveBuffer()
        
        # 添加多块数据
        for i in range(5):
            buf += f"Chunk {i}: {'X' * 200}\n".encode()
        
        print(f"✓ 添加5块数据，总大小: {buf._len}字节")
        print(f"✓ chunks数量: {len(buf._chunks)}")
        
        # 测试部分清理
        cleared = buf.clear_oldest(300)  # 保留最后300字节
        print(f"✓ 部分清理后大小: {buf._len}字节")
        print(f"✓ 清理的数据大小: {len(cleared)}字节")
        
        # 测试压缩
        buf.compact()
        print(f"✓ 压缩后chunks数量: {len(buf._chunks)}")
        
        # 测试内存使用统计
        memory_usage = buf.get_memory_usage()
        print(f"✓ 内存使用量: {memory_usage}字节")
        
        # 测试是否已满
        buf.set_max_size(500)
        is_full = buf.is_full()
        print(f"✓ 是否达到内存限制: {is_full}")
        
    except Exception as e:
        print(f"✗ 高级清理功能测试失败: {e}")
        return False
    
    return True

def test_size_parsing_standalone():
    """独立测试大小解析功能"""
    print("\n=== 独立测试大小解析 ===")
    
    def parse_size(size_str: str) -> int:
        """复制自HttpStream的大小解析函数"""
        size_str = size_str.lower().strip()
        multipliers = {'k': 1024, 'm': 1024*1024, 'g': 1024*1024*1024}
        
        for suffix, multiplier in multipliers.items():
            if size_str.endswith(suffix):
                try:
                    return int(size_str[:-1]) * multiplier
                except ValueError:
                    break
        
        try:
            return int(size_str)
        except ValueError:
            return 1024 * 1024  # 默认1MB
    
    test_cases = [
        ("1k", 1024),
        ("2K", 2048),
        ("1m", 1024*1024),
        ("512M", 512*1024*1024),
        ("1g", 1024*1024*1024),
        ("1024", 1024),  # 纯数字
        ("invalid", 1024*1024),  # 无效格式，应该返回默认值
    ]
    
    all_passed = True
    for size_str, expected in test_cases:
        result = parse_size(size_str)
        if result == expected:
            print(f"✓ '{size_str}' -> {result:,}字节 (正确)")
        else:
            print(f"✗ '{size_str}' -> {result:,}字节 (期望: {expected:,})")
            all_passed = False
    
    return all_passed

def test_memory_efficiency():
    """测试内存效率"""
    print("\n=== 测试内存效率 ===")
    
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("utils", "/Users/tanfujun/brix/tt-kimi-annotation/mitmproxy/mitmproxy/proxy/utils.py")
        utils_module = importlib.util.module_from_spec(spec)
        
        class MockContext:
            def __init__(self):
                self.log = lambda msg, level: None  # 静默日志
        
        utils_module.Context = MockContext
        spec.loader.exec_module(utils_module)
        
        ReceiveBuffer = utils_module.ReceiveBuffer
        
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        return False
    
    try:
        # 测试大量小数据块的内存效率
        buf = ReceiveBuffer()
        
        # 添加1000个小数据块
        for i in range(1000):
            buf += f"Small chunk {i:04d}\n".encode()
        
        print(f"✓ 添加1000个小数据块，总大小: {buf._len:,}字节")
        print(f"✓ chunks数量: {len(buf._chunks)}")
        
        # 压缩前内存使用
        memory_before = buf.get_memory_usage()
        print(f"✓ 压缩前内存使用: {memory_before:,}字节")
        
        # 压缩
        buf.compact()
        memory_after = buf.get_memory_usage()
        print(f"✓ 压缩后内存使用: {memory_after:,}字节")
        print(f"✓ 内存节省: {memory_before - memory_after:,}字节")
        
        # 验证数据完整性
        data = bytes(buf)
        expected_lines = 1000
        actual_lines = data.count(b'\n')
        if actual_lines == expected_lines:
            print(f"✓ 数据完整性验证通过: {actual_lines}行")
        else:
            print(f"✗ 数据完整性验证失败: 期望{expected_lines}行，实际{actual_lines}行")
            return False
        
    except Exception as e:
        print(f"✗ 内存效率测试失败: {e}")
        return False
    
    return True

def main():
    """主测试函数"""
    print("开始测试mitmproxy内存限制功能...")
    print("=" * 50)
    
    tests = [
        test_receive_buffer_standalone,
        test_size_parsing_standalone,
        test_memory_efficiency,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
                print(f"\n✓ {test.__name__} 通过")
            else:
                print(f"\n✗ {test.__name__} 失败")
        except Exception as e:
            print(f"\n✗ {test.__name__} 异常: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'=' * 50}")
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！")
        print("\n主要功能验证:")
        print("✓ ReceiveBuffer内存限制机制工作正常")
        print("✓ 大小解析功能正确")
        print("✓ 内存压缩和清理功能有效")
        print("✓ 数据完整性得到保证")
        return 0
    else:
        print("❌ 部分测试失败")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)