#!/usr/bin/env python3
"""
运行WikiSQL验证的便捷脚本
"""

import os
import sys
from pathlib import Path
from wikisql_validator import WikiSQLValidator

def find_wikisql_files():
    """自动查找WikiSQL相关文件"""
    # 可能的WikiSQL路径
    possible_paths = [
        "WikiSQL",
        "../WikiSQL", 
        "./WikiSQL"
    ]
    
    for path in possible_paths:
        wikisql_path = Path(path)
        if wikisql_path.exists():
            data_dir = wikisql_path / "data"
            if data_dir.exists():
                return wikisql_path
    
    return None

def find_prediction_files():
    """查找预测文件"""
    current_dir = Path(".")
    prediction_files = list(current_dir.glob("predictions_*.jsonl"))
    return prediction_files

def main():
    """主函数"""
    print("=" * 60)
    print("🔍 WikiSQL验证器")
    print("=" * 60)
    
    # 1. 查找WikiSQL路径
    print("📁 查找WikiSQL文件...")
    wikisql_path = find_wikisql_files()
    
    if not wikisql_path:
        print("❌ 未找到WikiSQL目录")
        print("请确保WikiSQL目录存在于当前目录或上级目录")
        return
    
    print(f"✅ 找到WikiSQL: {wikisql_path.absolute()}")
    
    # 2. 查找预测文件
    print("\n📄 查找预测文件...")
    prediction_files = find_prediction_files()
    
    if not prediction_files:
        print("❌ 未找到预测文件")
        print("请先运行 generate_wikisql_predictions.py 生成预测文件")
        return
    
    print(f"✅ 找到 {len(prediction_files)} 个预测文件:")
    for i, file in enumerate(prediction_files):
        print(f"  {i+1}. {file}")
    
    # 3. 选择预测文件
    if len(prediction_files) == 1:
        selected_file = prediction_files[0]
        print(f"\n🎯 自动选择: {selected_file}")
    else:
        print(f"\n请选择要验证的预测文件 (1-{len(prediction_files)}):")
        try:
            choice = int(input("输入编号: ")) - 1
            if 0 <= choice < len(prediction_files):
                selected_file = prediction_files[choice]
            else:
                print("❌ 无效选择")
                return
        except ValueError:
            print("❌ 请输入有效数字")
            return
    
    # 4. 确定数据分割
    filename = selected_file.name
    if "dev" in filename:
        split = "dev"
    elif "test" in filename:
        split = "test"
    elif "train" in filename:
        split = "train"
    else:
        split = input("请输入数据分割 (dev/test/train, 默认dev): ").strip() or "dev"
    
    # 5. 构建文件路径
    source_file = wikisql_path / "data" / f"{split}.jsonl"
    db_file = wikisql_path / "data" / f"{split}.db"
    predictions_file = selected_file
    
    # 6. 验证文件存在
    missing_files = []
    if not source_file.exists():
        missing_files.append(str(source_file))
    if not db_file.exists():
        missing_files.append(str(db_file))
    if not predictions_file.exists():
        missing_files.append(str(predictions_file))
    
    if missing_files:
        print(f"❌ 缺少文件:")
        for file in missing_files:
            print(f"  - {file}")
        return
    
    # 7. 执行验证
    print(f"\n🚀 开始验证...")
    print(f"  源文件: {source_file}")
    print(f"  数据库: {db_file}")
    print(f"  预测文件: {predictions_file}")
    
    try:
        # 创建验证器
        validator = WikiSQLValidator(
            str(source_file),
            str(db_file), 
            str(predictions_file)
        )
        
        # 执行评估
        summary = validator.evaluate()
        
        # 生成报告文件名
        report_file = f"evaluation_report_{split}_{selected_file.stem}.json"
        
        # 保存详细报告
        validator.save_detailed_report(summary, report_file)
        
        # 打印样本结果
        validator.print_sample_results(summary, num_samples=3)
        
        # 打印最终结果
        print(f"\n{'='*60}")
        print(f"🎯 最终评估结果:")
        print(f"{'='*60}")
        print(f"📊 总问题数: {summary['total_questions']}")
        print(f"✅ 正确答案: {summary['correct_answers']}")
        print(f"❌ 错误数量: {summary['errors']}")
        print(f"🎯 准确率: {summary['accuracy']:.4f} ({summary['accuracy']*100:.2f}%)")
        print(f"⚠️  错误率: {summary['error_rate']:.4f} ({summary['error_rate']*100:.2f}%)")
        print(f"{'='*60}")
        print(f"📄 详细报告已保存: {report_file}")
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()