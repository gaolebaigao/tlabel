#!/usr/bin/env python3
"""
README Freshness Check

Ensures that code examples in README.md are valid and can be executed.
This test extracts Python code blocks from README and verifies imports work.

Related to: LeRobot PR #4032 review feedback
"""

import re
import ast
import pytest
from pathlib import Path


# Find README.md (handle both repo root and package install scenarios)
def find_readme():
    """Locate README.md relative to this test file or the package root."""
    # Try relative to this test file (in tests/unit/)
    test_dir = Path(__file__).parent
    readme_candidates = [
        test_dir.parent.parent / "README.md",  # tests/unit/../../README.md
        test_dir.parent.parent.parent / "README.md",  # if installed as package
        Path.cwd() / "README.md",
    ]
    for candidate in readme_candidates:
        if candidate.exists():
            return candidate
    return None


def extract_python_code_blocks(readme_path):
    """Extract Python code blocks from markdown file."""
    if not readme_path or not readme_path.exists():
        return []
    
    content = readme_path.read_text(encoding="utf-8")
    # Match ```python ... ``` blocks
    pattern = r"```python\s*\n(.*?)```"
    matches = re.findall(pattern, content, re.DOTALL)
    return [m.strip() for m in matches if m.strip()]


def extract_import_statements(code_block):
    """Extract import statements from a code block."""
    imports = []
    try:
        tree = ast.parse(code_block)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
    except SyntaxError:
        pass  # Skip non-parseable blocks
    return imports


class TestReadmeFreshness:
    """Test suite for README.md code example freshness."""
    
    @pytest.fixture
    def readme_path(self):
        """Get README.md path."""
        path = find_readme()
        if path is None:
            pytest.skip("README.md not found")
        return path
    
    @pytest.fixture
    def code_blocks(self, readme_path):
        """Extract Python code blocks from README."""
        blocks = extract_python_code_blocks(readme_path)
        if not blocks:
            pytest.skip("No Python code blocks found in README.md")
        return blocks
    
    def test_readme_exists(self, readme_path):
        """Verify README.md exists."""
        assert readme_path.exists(), f"README.md not found at {readme_path}"
        assert readme_path.stat().st_size > 100, "README.md seems too small"
    
    def test_readme_has_code_examples(self, code_blocks):
        """Verify README has at least one Python code example."""
        assert len(code_blocks) >= 1, "README should have at least one Python code block"
    
    def test_tlabel_import_works(self, code_blocks):
        """Verify that 'import tlabel' works."""
        # Find code blocks that import tlabel
        tlabel_blocks = [b for b in code_blocks if "import tlabel" in b or "from tlabel" in b]
        
        if not tlabel_blocks:
            pytest.skip("No tlabel imports found in README")
        
        # Try to execute the import
        try:
            import tlabel
            assert hasattr(tlabel, "__version__"), "tlabel should have __version__"
        except ImportError as e:
            pytest.fail(f"Failed to import tlabel: {e}")
    
    def test_readme_imports_are_valid(self, code_blocks):
        """Verify all tlabel-related imports in README are valid."""
        all_imports = set()
        
        for block in code_blocks:
            imports = extract_import_statements(block)
            tlabel_imports = [i for i in imports if i.startswith("tlabel")]
            all_imports.update(tlabel_imports)
        
        if not all_imports:
            pytest.skip("No tlabel imports found in README code blocks")
        
        # Try to import each module
        failed_imports = []
        for module_name in all_imports:
            try:
                __import__(module_name)
            except ImportError as e:
                failed_imports.append(f"{module_name}: {e}")
        
        if failed_imports:
            pytest.fail(f"README contains invalid imports:\n" + "\n".join(failed_imports))
    
    def test_readme_api_calls_are_valid(self, code_blocks):
        """Verify API calls in README use valid methods."""
        # Check for common deprecated or removed APIs
        deprecated_patterns = [
            (r"tlabel\.load_v2\s*\(", "load_v2() is deprecated, use load() instead"),
            (r"from lerobot\.common\.datasets", "LeRobot import path deprecated, use 'from lerobot.datasets import ...'"),
        ]
        
        readme_content = ""
        readme_path = find_readme()
        if readme_path:
            readme_content = readme_path.read_text(encoding="utf-8")
        
        found_deprecated = []
        for pattern, message in deprecated_patterns:
            if re.search(pattern, readme_content):
                found_deprecated.append(f"- {message}")
        
        if found_deprecated:
            pytest.fail("README contains deprecated API usage:\n" + "\n".join(found_deprecated))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
