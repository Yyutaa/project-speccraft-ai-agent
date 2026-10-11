import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="SpecCraft project scaffold")
    parser.add_argument("--version", action="store_true", help="show scaffold version")
    args = parser.parse_args()
    if args.version:
        print("speccraft-project-scaffold 0.1.0")
        return
    print("SpecCraft 项目脚手架已就绪。")
    print("当前提供基础工程结构，后续能力见 README.md。")


if __name__ == "__main__":
    main()
