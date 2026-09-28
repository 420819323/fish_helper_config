#!/usr/bin/env python3
# 闲鱼猪手 配置文件 (+12 位移) 加密 / 解密工具
# 算法来源: https://www.cnblogs.com/azwhikaru/p/17045056.html
# 规则: 加密 = 每个字符 Unicode 码点 +12 ; 解密 = 每个字符码点 -12
# 用途: 按版本的 hook 配置文件(类名/方法名映射)是 +12 加密的,
#       需要解密后才能阅读/修改, 改完再加密回传。

import argparse
import sys

SHIFT = 12


def transform(text: str, mode: str) -> str:
    out = []
    for ch in text:
        cp = ord(ch)
        cp = cp + SHIFT if mode == "encrypt" else cp - SHIFT
        out.append(chr(cp))
    return "".join(out)


def main():
    ap = argparse.ArgumentParser(description="闲鱼猪手配置 +12 加/解密")
    ap.add_argument("input", help="输入文件路径")
    ap.add_argument("-o", "--output", help="输出文件路径 (缺省输出到 stdout)")
    ap.add_argument(
        "-m",
        "--mode",
        choices=["decrypt", "encrypt"],
        default="decrypt",
        help="decrypt = 配置 -12 还原明文(默认); encrypt = 明文 +12 加密",
    )
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = f.read()

    result = transform(data, args.mode)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        label = "加密" if args.mode == "encrypt" else "解密"
        print(f"已{label} -> {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(result)


if __name__ == "__main__":
    main()
