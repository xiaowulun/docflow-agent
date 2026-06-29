"""
OfficeCLI 工具集成测试。

需要本地已安装 officecli 二进制，否则这些测试会被跳过。
"""

import os
import tempfile

import pytest

from packages.tooling import ToolRegistry
from packages.tooling.officecli import is_available

pytestmark = pytest.mark.skipif(
    not is_available(),
    reason="officecli 未安装",
)


class TestOfficeCLIBase:
    """验证底层封装可用。"""

    def test_is_available(self):
        assert is_available()

    def test_create_docx(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.docx")
            result = ToolRegistry.call("create_docx", path=path)
            assert result.get("success") is True
            assert os.path.exists(path)


class TestWordFlow:
    """Word 创建 -> 写入 -> 查看 完整流程。"""

    def test_create_and_edit_docx(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "report.docx")

            # 创建
            r = ToolRegistry.call("create_docx", path=path)
            assert r.get("success") is True

            # 添加标题
            r = ToolRegistry.call(
                "add_docx",
                file_path=path,
                parent="/body",
                element_type="paragraph",
                props={"text": "Q4 业务报告", "style": "Heading1"},
            )
            assert r.get("success") is True

            # 添加正文
            r = ToolRegistry.call(
                "add_docx",
                file_path=path,
                parent="/body",
                element_type="paragraph",
                props={"text": "本季度营收增长 25%。"},
            )
            assert r.get("success") is True

            # 查看大纲
            outline = ToolRegistry.call("view_docx", file_path=path, mode="outline")
            assert outline.get("success") is True
            headings = outline["data"].get("headings", [])
            assert any("Q4 业务报告" in h.get("text", "") for h in headings)

            # 获取元素
            get_result = ToolRegistry.call("get_docx", file_path=path, path="/body/p[1]")
            assert get_result.get("success") is True


class TestExcelFlow:
    """Excel 创建 -> 写入 -> 查看 完整流程。"""

    def test_create_and_edit_xlsx(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "data.xlsx")

            r = ToolRegistry.call("create_xlsx", path=path)
            assert r.get("success") is True

            r = ToolRegistry.call(
                "set_xlsx",
                file_path=path,
                path="/Sheet1/A1",
                props={"value": "Name", "bold": "true"},
            )
            assert r.get("success") is True

            r = ToolRegistry.call(
                "set_xlsx",
                file_path=path,
                path="/Sheet1/A2",
                props={"value": "Alice"},
            )
            assert r.get("success") is True

            text = ToolRegistry.call("view_xlsx", file_path=path, mode="text")
            assert text.get("success") is True
            assert "Alice" in str(text["data"])


class TestPPTFlow:
    """PPT 创建 -> 写入 -> 查看 完整流程。"""

    def test_create_and_edit_pptx(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "deck.pptx")

            r = ToolRegistry.call("create_pptx", path=path)
            assert r.get("success") is True

            r = ToolRegistry.call(
                "add_pptx",
                file_path=path,
                parent="/",
                element_type="slide",
                props={"title": "Hello OfficeCLI"},
            )
            assert r.get("success") is True

            r = ToolRegistry.call(
                "add_pptx",
                file_path=path,
                parent="/slide[1]",
                element_type="shape",
                props={
                    "text": "营收增长 25%",
                    "x": "2cm",
                    "y": "5cm",
                    "font": "Arial",
                    "size": "24",
                },
            )
            assert r.get("success") is True

            outline = ToolRegistry.call("view_pptx", file_path=path, mode="outline")
            assert outline.get("success") is True
            assert "Hello OfficeCLI" in str(outline["data"])


class TestHelp:
    """帮助工具可用。"""

    def test_office_help(self):
        result = ToolRegistry.call("office_help", fmt="docx", element="paragraph")
        assert "stdout" in result
        assert "paragraph" in result["stdout"].lower()


class TestAdvancedWord:
    """Word 高级功能：batch/move/swap/clear/replace/validate。"""

    def test_batch_docx(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "batch.docx")
            ToolRegistry.call("create_docx", path=path)

            commands = [
                {
                    "command": "add",
                    "parent": "/body",
                    "type": "paragraph",
                    "props": {"text": "第一段"},
                },
                {
                    "command": "add",
                    "parent": "/body",
                    "type": "paragraph",
                    "props": {"text": "第二段"},
                },
                {
                    "command": "add",
                    "parent": "/body",
                    "type": "paragraph",
                    "props": {"text": "第三段"},
                },
            ]
            r = ToolRegistry.call("batch_docx", file_path=path, commands=commands)
            assert r.get("success") is True

            outline = ToolRegistry.call("view_docx", file_path=path, mode="text")
            assert outline.get("success") is True
            text = str(outline["data"])
            assert "第一段" in text
            assert "第二段" in text
            assert "第三段" in text

    def test_move_docx(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "move.docx")
            ToolRegistry.call("create_docx", path=path)

            for text in ["A", "B", "C"]:
                ToolRegistry.call(
                    "add_docx",
                    file_path=path,
                    parent="/body",
                    element_type="paragraph",
                    props={"text": text},
                )

            r = ToolRegistry.call(
                "move_docx",
                file_path=path,
                path="/body/p[1]",
                after="/body/p[3]",
            )
            assert r.get("success") is True

    def test_swap_docx(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "swap.docx")
            ToolRegistry.call("create_docx", path=path)

            for text in ["First", "Second"]:
                ToolRegistry.call(
                    "add_docx",
                    file_path=path,
                    parent="/body",
                    element_type="paragraph",
                    props={"text": text},
                )

            r = ToolRegistry.call(
                "swap_docx",
                file_path=path,
                path1="/body/p[1]",
                path2="/body/p[2]",
            )
            assert r.get("success") is True

    def test_clear_docx(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "clear.docx")
            ToolRegistry.call("create_docx", path=path)

            for i in range(3):
                ToolRegistry.call(
                    "add_docx",
                    file_path=path,
                    parent="/body",
                    element_type="paragraph",
                    props={"text": f"段落{i}"},
                )

            r = ToolRegistry.call("clear_docx", file_path=path)
            assert r.get("success") is True

            outline = ToolRegistry.call("view_docx", file_path=path, mode="text")
            assert outline.get("success") is True
            text = str(outline["data"])
            assert "段落0" not in text

    def test_replace_docx(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "replace.docx")
            ToolRegistry.call("create_docx", path=path)

            ToolRegistry.call(
                "add_docx",
                file_path=path,
                parent="/body",
                element_type="paragraph",
                props={"text": "旧内容"},
            )

            new_content = [
                {"type": "paragraph", "props": {"text": "新标题", "style": "Heading1"}},
                {"type": "paragraph", "props": {"text": "新正文"}},
            ]
            r = ToolRegistry.call("replace_docx", file_path=path, new_content=new_content)
            assert r.get("success") is True

            outline = ToolRegistry.call("view_docx", file_path=path, mode="text")
            text = str(outline["data"])
            assert "新标题" in text
            assert "新正文" in text
            assert "旧内容" not in text

    def test_validate_docx(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "validate.docx")
            ToolRegistry.call("create_docx", path=path)
            ToolRegistry.call(
                "add_docx",
                file_path=path,
                parent="/body",
                element_type="paragraph",
                props={"text": "验证测试"},
            )

            r = ToolRegistry.call("validate_docx", file_path=path)
            assert r.get("success") is True


class TestAdvancedExcel:
    """Excel 高级功能：batch/clear/replace/validate。"""

    def test_batch_xlsx(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "batch.xlsx")
            ToolRegistry.call("create_xlsx", path=path)

            commands = [
                {"command": "set", "path": "/Sheet1/A1", "props": {"value": "姓名"}},
                {"command": "set", "path": "/Sheet1/B1", "props": {"value": "年龄"}},
                {"command": "set", "path": "/Sheet1/A2", "props": {"value": "张三"}},
                {"command": "set", "path": "/Sheet1/B2", "props": {"value": "28"}},
            ]
            r = ToolRegistry.call("batch_xlsx", file_path=path, commands=commands)
            assert r.get("success") is True

            text = ToolRegistry.call("view_xlsx", file_path=path, mode="text")
            assert "张三" in str(text["data"])

    def test_clear_xlsx(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "clear.xlsx")
            ToolRegistry.call("create_xlsx", path=path)
            ToolRegistry.call(
                "set_xlsx",
                file_path=path,
                path="/Sheet1/A1",
                props={"value": "测试数据"},
            )

            r = ToolRegistry.call("clear_xlsx", file_path=path)
            assert r.get("success") is True

    def test_validate_xlsx(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "validate.xlsx")
            ToolRegistry.call("create_xlsx", path=path)

            r = ToolRegistry.call("validate_xlsx", file_path=path)
            assert r.get("success") is True


class TestAdvancedPPT:
    """PPT 高级功能：batch/clear/replace/validate。"""

    def test_batch_pptx(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "batch.pptx")
            ToolRegistry.call("create_pptx", path=path)

            commands = [
                {
                    "command": "add",
                    "parent": "/",
                    "type": "slide",
                    "props": {"title": "第一页"},
                },
                {
                    "command": "add",
                    "parent": "/",
                    "type": "slide",
                    "props": {"title": "第二页"},
                },
            ]
            r = ToolRegistry.call("batch_pptx", file_path=path, commands=commands)
            assert r.get("success") is True

            outline = ToolRegistry.call("view_pptx", file_path=path, mode="outline")
            assert outline.get("success") is True
            text = str(outline["data"])
            assert "第一页" in text
            assert "第二页" in text

    def test_clear_pptx(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "clear.pptx")
            ToolRegistry.call("create_pptx", path=path)
            ToolRegistry.call(
                "add_pptx",
                file_path=path,
                parent="/",
                element_type="slide",
                props={"title": "待删除"},
            )

            r = ToolRegistry.call("clear_pptx", file_path=path)
            assert r.get("success") is True

    def test_replace_pptx(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "replace.pptx")
            ToolRegistry.call("create_pptx", path=path)
            ToolRegistry.call(
                "add_pptx",
                file_path=path,
                parent="/",
                element_type="slide",
                props={"title": "旧幻灯片"},
            )

            new_content = [
                {"type": "slide", "props": {"title": "新幻灯片1"}},
                {"type": "slide", "props": {"title": "新幻灯片2"}},
            ]
            r = ToolRegistry.call("replace_pptx", file_path=path, new_content=new_content)
            assert r.get("success") is True

            outline = ToolRegistry.call("view_pptx", file_path=path, mode="outline")
            text = str(outline["data"])
            assert "新幻灯片1" in text
            assert "旧幻灯片" not in text

    def test_validate_pptx(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "validate.pptx")
            ToolRegistry.call("create_pptx", path=path)

            r = ToolRegistry.call("validate_pptx", file_path=path)
            assert r.get("success") is True


class TestSessionMode:
    """驻留模式：open/close/save。"""

    def test_open_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "session.docx")
            ToolRegistry.call("create_docx", path=path)

            r = ToolRegistry.call("office_open", file_path=path)
            assert r.get("success") is True

            r = ToolRegistry.call("office_close", file_path=path)
            assert r.get("success") is True

    def test_open_save_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "session_save.docx")
            ToolRegistry.call("create_docx", path=path)

            r = ToolRegistry.call("office_open", file_path=path)
            assert r.get("success") is True

            r = ToolRegistry.call("office_save", file_path=path)
            assert r.get("success") is True

            r = ToolRegistry.call("office_close", file_path=path)
            assert r.get("success") is True
