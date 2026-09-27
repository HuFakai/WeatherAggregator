#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeatherAggregator 线上 API 连通性与功能自动化测试脚本
仅使用 Python 标准库 (urllib / json / time)，无需安装任何额外依赖，开箱即用。

使用方法:
    python3 scripts/test_live_api.py
    或者:
    python3 scripts/test_live_api.py --host https://weather.zizheng7zfb.com --key ck_1e4e10aedc7c4644
"""

import sys
import os
import time
import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

DEFAULT_HOST = "https://weather.zizheng7zfb.com"
DEFAULT_KEY = "ck_1e4e10aedc7c4644"

# 终端色彩高亮
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

def log_section(title):
    print(f"\n{BOLD}{CYAN}{'='*15} {title} {'='*15}{RESET}")

def make_request(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    start_time = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            elapsed = (time.perf_counter() - start_time) * 1000
            status_code = resp.getcode()
            body_bytes = resp.read()
            data = json.loads(body_bytes.decode("utf-8"))
            return True, status_code, elapsed, data
    except urllib.error.HTTPError as e:
        elapsed = (time.perf_counter() - start_time) * 1000
        try:
            err_data = json.loads(e.read().decode("utf-8"))
        except Exception:
            err_data = {"detail": str(e)}
        return False, e.code, elapsed, err_data
    except Exception as e:
        elapsed = (time.perf_counter() - start_time) * 1000
        return False, 0, elapsed, {"error": str(e)}

def print_weather_brief(data):
    if not isinstance(data, dict):
        return
    city_name = data.get("city_name", "未知")
    city_id = data.get("_id", "-")
    last_updated = data.get("last_updated_at", "-")
    sources = data.get("sources", {})
    
    print(f"  📍 城市: {BOLD}{city_name}{RESET} (ID: {city_id})")
    print(f"  🕒 报文生成时间: {last_updated}")
    print(f"  🌐 聚合上游数据源: {GREEN}{list(sources.keys())}{RESET}")

    # 打印今日实况/首日预报简报
    for src_name, days in sources.items():
        if isinstance(days, list) and len(days) > 0:
            today = days[0]
            temp_high = today.get("temp_high", "-")
            temp_low = today.get("temp_low", "-")
            w_day = today.get("weather_day", "-")
            w_night = today.get("weather_night", "-")
            aqi = today.get("aqi", "-")
            aqi_level = today.get("aqi_level", "-")
            lifestyles = today.get("lifestyle", [])

            print(f"     • [{src_name}] 今日天气: {w_day}/{w_night} | 温度: {temp_low}°C ~ {temp_high}°C | AQI: {aqi} ({aqi_level})")
            if lifestyles:
                brief_life = [f"{item.get('title')}:{item.get('level')}" for item in lifestyles[:3]]
                print(f"       生活指数: {', '.join(brief_life)}")

def run_tests(base_url, api_key):
    print(f"{BOLD}======================================================{RESET}")
    print(f"{BOLD}  WeatherAggregator 线上生产 API 连通性测试套件{RESET}")
    print(f"  目标服务器: {CYAN}{base_url}{RESET}")
    print(f"  测试 Key:   {YELLOW}{api_key}{RESET}")
    print(f"  测试时间:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{BOLD}======================================================{RESET}")

    test_cases = [
        {
            "name": "用例 1: Path 传参 + Header 鉴权 (北京)",
            "url": f"{base_url}/api/v1/weather/{urllib.parse.quote('北京')}",
            "headers": {"X-API-Key": api_key},
            "expect_status": 200
        },
        {
            "name": "用例 2: Query 传参 + Header 鉴权 (上海)",
            "url": f"{base_url}/api/v1/weather?city={urllib.parse.quote('上海')}",
            "headers": {"X-API-Key": api_key},
            "expect_status": 200
        },
        {
            "name": "用例 3: 城市编码 (adcode) 传参 (广州 440100)",
            "url": f"{base_url}/api/v1/weather/440100",
            "headers": {"X-API-Key": api_key},
            "expect_status": 200
        },
        {
            "name": "用例 4: Query 参数携带 Key (深圳 ?city=深圳&key=...)",
            "url": f"{base_url}/api/v1/weather?city={urllib.parse.quote('深圳')}&key={api_key}",
            "headers": {},
            "expect_status": 200
        },
        {
            "name": "用例 5: 非法 Key 拦截防御测试 (预期返回 401/403)",
            "url": f"{base_url}/api/v1/weather/{urllib.parse.quote('成都')}",
            "headers": {"X-API-Key": "invalid_mock_key_99999"},
            "expect_status": [401, 403]
        }
    ]

    total_passed = 0

    for idx, tc in enumerate(test_cases, 1):
        log_section(f"[{idx}/{len(test_cases)}] {tc['name']}")
        print(f"  URL: {tc['url']}")
        if tc["headers"]:
            print(f"  Headers: {tc['headers']}")

        ok, code, elapsed, data = make_request(tc["url"], tc["headers"])
        
        expected = tc["expect_status"]
        is_pass = (code in expected) if isinstance(expected, list) else (code == expected)

        if is_pass:
            total_passed += 1
            print(f"  {GREEN}✔ 测试通过{RESET} · 状态码: {code} · 响应延迟: {elapsed:.1f}ms")
            if code == 200:
                print_weather_brief(data)
            else:
                print(f"  网关拦截响应: {data}")
        else:
            print(f"  {RED}✘ 测试失败{RESET} · 实际状态码: {code} (预期: {expected}) · 响应延迟: {elapsed:.1f}ms")
            print(f"  响应内容: {data}")

    # 总结
    print(f"\n{BOLD}======================================================{RESET}")
    if total_passed == len(test_cases):
        print(f"{GREEN}{BOLD}🎉 全部用例通过! ({total_passed}/{len(test_cases)}){RESET}")
        print(f"线上 API 服务正常稳定运行，Key 鉴权与聚合接口工作良好。")
    else:
        print(f"{RED}{BOLD}⚠ 测试未全部通过: {total_passed}/{len(test_cases)} 通过{RESET}")
    print(f"{BOLD}======================================================{RESET}\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="WeatherAggregator 线上 API 测试工具")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"目标主机 (默认: {DEFAULT_HOST})")
    parser.add_argument("--key", default=DEFAULT_KEY, help=f"客户端 API Key (默认: {DEFAULT_KEY})")
    args = parser.parse_args()

    run_tests(args.host.rstrip("/"), args.key)
