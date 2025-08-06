#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动生成文件树和docsify侧边栏的脚本
用于全国大学生电子设计竞赛历年真题项目
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple

class TreeGenerator:
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir).resolve()
        self.ignore_patterns = [
            ".git", ".github", "node_modules", "__pycache__", 
            "tree.bak", ".nojekyll", "generate_tree.py",
            "index.html", "_sidebar.md", ".gitignore"
        ]
        
    def should_ignore(self, path: Path) -> bool:
        """检查是否应该忽略某个路径"""
        name = path.name
        return (
            name.startswith('.') and name not in ['.nojekyll'] or
            name in self.ignore_patterns or
            any(pattern in str(path) for pattern in self.ignore_patterns)
        )
    
    def get_file_info(self, file_path: Path) -> Dict:
        """获取文件信息"""
        stat = file_path.stat()
        return {
            "name": file_path.name,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "is_pdf": file_path.suffix.lower() == '.pdf',
            "is_doc": file_path.suffix.lower() in ['.doc', '.docx'],
            "is_excel": file_path.suffix.lower() in ['.xls', '.xlsx'],
            "is_image": file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']
        }
    
    def format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def extract_problem_info(self, filename: str) -> Tuple[str, str]:
        """从文件名提取题目信息"""
        # 移除文件扩展名
        name_without_ext = os.path.splitext(filename)[0]
        
        # 匹配模式：A题_标题 或 A_标题
        match = re.match(r'^([A-Z])(?:题)?[_\-](.+)$', name_without_ext)
        if match:
            letter, title = match.groups()
            return letter, title.replace('_', ' ').replace('-', ' ')
        
        # 匹配其他模式
        if name_without_ext.startswith('0_'):
            return "INFO", name_without_ext[2:].replace('_', ' ')
        
        return "FILE", name_without_ext.replace('_', ' ')
    
    def generate_readme_tree(self) -> str:
        """生成README文件树"""
        lines = ["```"]
        lines.append(".")
        
        # 统计信息
        total_files = 0
        total_dirs = 0
        
        def add_directory(dir_path: Path, prefix: str = ""):
            nonlocal total_files, total_dirs
            
            if self.should_ignore(dir_path):
                return
            
            try:
                items = sorted(dir_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
                
                for i, item in enumerate(items):
                    if self.should_ignore(item):
                        continue
                    
                    is_last = i == len(items) - 1
                    current_prefix = "└── " if is_last else "├── "
                    next_prefix = "    " if is_last else "│   "
                    
                    if item.is_dir():
                        lines.append(f"{prefix}{current_prefix}{item.name}")
                        total_dirs += 1
                        add_directory(item, prefix + next_prefix)
                    else:
                        lines.append(f"{prefix}{current_prefix}{item.name}")
                        total_files += 1
                        
            except PermissionError:
                pass
        
        add_directory(self.root_dir)
        lines.append("")
        lines.append(f"{total_dirs} directories, {total_files} files")
        lines.append("```")
        
        return "\n".join(lines)
    
    def generate_docsify_sidebar(self) -> str:
        """生成docsify侧边栏"""
        lines = ["* [**首页**](/)"]
        lines.append("* [**使用说明**](#使用说明)")
        lines.append("")
        
        # 获取所有年份目录
        year_dirs = []
        for item in self.root_dir.iterdir():
            if (item.is_dir() and 
                not self.should_ignore(item) and 
                re.match(r'^\d{4}$', item.name)):
                year_dirs.append(item)
        
        # 如果没有直接的年份目录，检查"真题"文件夹
        if not year_dirs:
            zhenti_dir = self.root_dir / "真题"
            if zhenti_dir.exists() and zhenti_dir.is_dir():
                for item in zhenti_dir.iterdir():
                    if (item.is_dir() and 
                        not self.should_ignore(item) and 
                        re.match(r'^\d{4}', item.name)):
                        year_dirs.append(item)
        
        # 按年份倒序排列（最新的在前面）
        year_dirs.sort(key=lambda x: x.name, reverse=True)
        
        # 添加年份和题目
        for year_dir in year_dirs:
            year = year_dir.name
            lines.append(f"* **{year}年**")
            
            # 获取该年份的所有文件
            try:
                files = []
                for file_path in year_dir.iterdir():
                    if file_path.is_file() and not self.should_ignore(file_path):
                        files.append(file_path)
                
                # 排序：首先是说明文件(0_开头)，然后按题目字母排序
                files.sort(key=lambda x: (
                    not x.name.startswith('0_'),  # 0_开头的文件排在前面
                    x.name.upper()
                ))
                
                for file_path in files:
                    filename = file_path.name
                    
                    # 跳过某些文件
                    if filename.startswith('.'):
                        continue
                    
                    # 提取题目信息
                    letter, title = self.extract_problem_info(filename)
                    
                    # 创建链接
                    link = f"#{year}/{filename}"
                    
                    if filename.startswith('0_'):
                        lines.append(f"  * [{title}]({link})")
                    else:
                        lines.append(f"  * **{letter}题** - [{title}]({link})")
                        
            except PermissionError:
                lines.append(f"  * 无法访问此年份的文件")
        
        # 添加综合测评部分
        zhongce_dir = self.root_dir / "综合测评"
        if zhongce_dir.exists() and zhongce_dir.is_dir():
            lines.append("")
            lines.append("* **综合测评**")
            
            try:
                files = [f for f in zhongce_dir.iterdir() 
                        if f.is_file() and not self.should_ignore(f)]
                files.sort(key=lambda x: x.name)
                
                for file_path in files:
                    filename = file_path.name
                    year_match = re.search(r'(\d{4})', filename)
                    if year_match:
                        year = year_match.group(1)
                        title = f"{year}年综合测评"
                    else:
                        title = os.path.splitext(filename)[0]
                    
                    link = f"#综合测评/{filename}"
                    lines.append(f"  * [{title}]({link})")
                    
            except PermissionError:
                lines.append("  * 无法访问综合测评文件")
        
        return "\n".join(lines) + "\n"
    
    def update_readme(self):
        """更新README文件中的目录树"""
        readme_path = self.root_dir / "README.md"
        
        if not readme_path.exists():
            print("README.md 文件不存在")
            return False
        
        try:
            # 读取现有内容
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 生成新的文件树
            new_tree = self.generate_readme_tree()
            
            # 替换文件树部分
            start_marker = "<!-- readme-tree start -->"
            end_marker = "<!-- readme-tree end -->"
            
            start_idx = content.find(start_marker)
            end_idx = content.find(end_marker)
            
            if start_idx != -1 and end_idx != -1:
                # 替换现有的文件树
                before = content[:start_idx + len(start_marker)]
                after = content[end_idx:]
                new_content = before + "\n" + new_tree + "\n" + after
            else:
                # 如果没有找到标记，在文件末尾添加
                new_content = content + "\n\n" + start_marker + "\n" + new_tree + "\n" + end_marker + "\n"
            
            # 写回文件
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print("README.md 文件树已更新")
            return True
            
        except Exception as e:
            print(f"更新README失败: {e}")
            return False
    
    def create_sidebar(self):
        """创建docsify侧边栏"""
        sidebar_content = self.generate_docsify_sidebar()
        sidebar_path = self.root_dir / "_sidebar.md"
        
        try:
            with open(sidebar_path, 'w', encoding='utf-8') as f:
                f.write(sidebar_content)
            print("_sidebar.md 已生成")
            return True
        except Exception as e:
            print(f"生成侧边栏失败: {e}")
            return False
    
    def generate_stats(self) -> Dict:
        """生成统计信息"""
        stats = {
            "total_files": 0,
            "total_dirs": 0,
            "years": [],
            "file_types": {},
            "total_size": 0
        }
        
        for root, dirs, files in os.walk(self.root_dir):
            root_path = Path(root)
            
            # 过滤忽略的目录
            dirs[:] = [d for d in dirs if not self.should_ignore(root_path / d)]
            
            stats["total_dirs"] += len(dirs)
            
            for file in files:
                file_path = root_path / file
                if self.should_ignore(file_path):
                    continue
                
                stats["total_files"] += 1
                
                # 统计文件类型
                ext = file_path.suffix.lower()
                stats["file_types"][ext] = stats["file_types"].get(ext, 0) + 1
                
                # 统计大小
                try:
                    stats["total_size"] += file_path.stat().st_size
                except:
                    pass
                
                # 统计年份
                year_match = re.search(r'\b(19|20)\d{2}\b', str(file_path))
                if year_match:
                    year = year_match.group()
                    if year not in stats["years"]:
                        stats["years"].append(year)
        
        stats["years"].sort()
        return stats

def main():
    """主函数"""
    # 设置输出编码为UTF-8
    import sys
    import io
    
    # Windows 下设置控制台编码
    if sys.platform == "win32":
        try:
            # 尝试设置控制台编码为UTF-8
            import locale
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
        except:
            pass
    
    generator = TreeGenerator()
    
    print("开始生成文件树和侧边栏...")
    
    # 更新README
    if generator.update_readme():
        print("README.md 更新成功")
    
    # 生成侧边栏
    if generator.create_sidebar():
        print("侧边栏生成成功")
    
    # 显示统计信息
    stats = generator.generate_stats()
    print(f"\n统计信息:")
    print(f"   总文件数: {stats['total_files']}")
    print(f"   总目录数: {stats['total_dirs']}")
    print(f"   涵盖年份: {len(stats['years'])} 年 ({min(stats['years']) if stats['years'] else 'N/A'} - {max(stats['years']) if stats['years'] else 'N/A'})")
    print(f"   总大小: {generator.format_file_size(stats['total_size'])}")
    print(f"   文件类型: {dict(sorted(stats['file_types'].items(), key=lambda x: x[1], reverse=True))}")
    
    print("\n完成!")

if __name__ == "__main__":
    main()