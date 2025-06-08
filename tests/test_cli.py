"""Tests for MSFW CLI functionality."""

import pytest
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from msfw.cli import (
    create_project,
    _create_module_util as create_module,
    _create_plugin_util as create_plugin,
    _run_dev_util as run_dev,
    main,
    generate_module_template,
    generate_plugin_template,
)


@pytest.mark.unit
class TestCLIFunctions:
    """Test individual CLI functions."""
    
    def test_generate_module_template(self):
        """Test module template generation."""
        template = generate_module_template("TestModule", "test_description")
        
        assert "class TestModule(Module)" in template
        assert "test_description" in template
        assert "def register_routes" in template
        assert "@router.get" in template
    
    def test_generate_plugin_template(self):
        """Test plugin template generation."""
        template = generate_plugin_template("TestPlugin", "test_description")
        
        assert "class TestPlugin(Plugin)" in template
        assert "test_description" in template
        assert "async def setup" in template
        assert "register_hook" in template
    
    def test_create_project(self, temp_dir):
        """Test project creation."""
        project_name = "test_project"
        project_path = temp_dir / project_name
        
        create_project(str(project_path))
        
        # Check that project structure was created
        assert project_path.exists()
        assert (project_path / "main.py").exists()
        assert (project_path / "config" / "settings.toml").exists()
        assert (project_path / "modules").exists()
        assert (project_path / "plugins").exists()
        assert (project_path / "requirements.txt").exists()
        assert (project_path / "README.md").exists()
        
        # Check main.py content
        main_content = (project_path / "main.py").read_text()
        assert "MSFWApplication" in main_content
        assert "Config" in main_content
    
    def test_create_project_existing_directory(self, temp_dir):
        """Test creating project in existing directory."""
        project_path = temp_dir / "existing_project"
        project_path.mkdir()
        
        with pytest.raises(ValueError, match="Directory already exists"):
            create_project(str(project_path))
    
    def test_create_module(self, mock_project_structure):
        """Test module creation."""
        module_name = "test_module"
        description = "Test module description"
        
        create_module(str(mock_project_structure), module_name, description)
        
        # Check that module file was created
        module_file = mock_project_structure / "modules" / f"{module_name}.py"
        assert module_file.exists()
        
        # Check content
        content = module_file.read_text()
        assert "class TestModule(Module)" in content
        assert description in content
    
    def test_create_module_invalid_name(self, mock_project_structure):
        """Test module creation with invalid name."""
        with pytest.raises(ValueError, match="Invalid module name"):
            create_module(str(mock_project_structure), "123invalid", "Description")
        
        with pytest.raises(ValueError, match="Invalid module name"):
            create_module(str(mock_project_structure), "invalid-name", "Description")
    
    def test_create_plugin(self, mock_project_structure):
        """Test plugin creation."""
        plugin_name = "test_plugin"
        description = "Test plugin description"
        
        create_plugin(str(mock_project_structure), plugin_name, description)
        
        # Check that plugin file was created
        plugin_file = mock_project_structure / "plugins" / f"{plugin_name}.py"
        assert plugin_file.exists()
        
        # Check content
        content = plugin_file.read_text()
        assert "class TestPlugin(Plugin)" in content
        assert description in content
    
    def test_create_plugin_invalid_name(self, mock_project_structure):
        """Test plugin creation with invalid name."""
        with pytest.raises(ValueError, match="Invalid plugin name"):
            create_plugin(str(mock_project_structure), "123invalid", "Description")
    
    @patch('subprocess.run')
    def test_run_dev(self, mock_subprocess, mock_project_structure):
        """Test development server run."""
        run_dev(str(mock_project_structure))
        
        # Should call uvicorn
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "uvicorn" in call_args
        assert "main:app" in call_args
        assert "--reload" in call_args


@pytest.mark.integration
class TestCLIIntegration:
    """Test CLI integration using Typer's testing framework."""
    
    def test_main_init_command(self, temp_dir):
        """Test main function with init command."""
        from typer.testing import CliRunner
        from msfw.cli import app
        import os
        
        runner = CliRunner()
        project_name = "test_project"
        
        # Change to temp directory and run command
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = runner.invoke(app, ["init", project_name])
            
            # Check command executed successfully
            assert result.exit_code == 0
            assert "Created MSFW project" in result.stdout
            
            # Verify project was created
            project_path = temp_dir / project_name
            assert project_path.exists()
            assert (project_path / "main.py").exists()
        finally:
            os.chdir(original_cwd)
    
    def test_main_create_module_command(self, temp_dir):
        """Test main function with create-module command."""
        from typer.testing import CliRunner
        from msfw.cli import app
        import os
        
        runner = CliRunner()
        
        # Create modules directory first
        modules_dir = temp_dir / "modules"
        modules_dir.mkdir()
        
        # Change to temp directory and run command
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = runner.invoke(app, [
                "create-module", 
                "test_module", 
                "--description", "Test description"
            ])
            
            # Check command executed successfully
            assert result.exit_code == 0
            
            # Verify module was created
            module_dir = modules_dir / "test_module"
            assert module_dir.exists()
            assert (module_dir / "__init__.py").exists()
        finally:
            os.chdir(original_cwd)
    
    def test_main_create_plugin_command(self, temp_dir):
        """Test main function with create-plugin command."""
        from typer.testing import CliRunner
        from msfw.cli import app
        import os
        
        runner = CliRunner()
        
        # Create plugins directory first
        plugins_dir = temp_dir / "plugins"
        plugins_dir.mkdir()
        
        # Change to temp directory and run command
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = runner.invoke(app, [
                "create-plugin", 
                "test_plugin",
                "--description", "Test plugin"
            ])
            
            # Check command executed successfully  
            assert result.exit_code == 0
            
            # Verify plugin was created (as .py file, not directory)
            plugin_file = plugins_dir / "test_plugin.py"
            assert plugin_file.exists()
            
            # Verify content
            content = plugin_file.read_text()
            assert "class Test_PluginPlugin(Plugin)" in content
        finally:
            os.chdir(original_cwd)
    
    @patch('uvicorn.run')
    def test_main_dev_command(self, mock_uvicorn, temp_dir):
        """Test main function with dev command."""
        from typer.testing import CliRunner
        from msfw.cli import app
        import os
        
        runner = CliRunner()
        
        # Create main.py file
        (temp_dir / "main.py").write_text("# Mock main file")
        
        # Change to temp directory and run command
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = runner.invoke(app, ["dev"])
            
            # Check command executed successfully
            assert result.exit_code == 0
            
            # Verify uvicorn.run was called with correct parameters
            mock_uvicorn.assert_called_once_with(
                "main:app",
                host="0.0.0.0",
                port=8000,
                reload=True,
                workers=1,
            )
        finally:
            os.chdir(original_cwd)


@pytest.mark.e2e
class TestCLIEndToEnd:
    """End-to-end CLI tests."""
    
    def test_full_project_workflow(self, temp_dir):
        """Test complete project creation and setup workflow."""
        project_name = "test_e2e_project"
        project_path = temp_dir / project_name
        
        # Create project
        create_project(str(project_path))
        
        # Verify project structure
        assert project_path.exists()
        assert (project_path / "main.py").exists()
        assert (project_path / "modules").exists()
        assert (project_path / "plugins").exists()
        
        # Create a module
        create_module(str(project_path), "users", "User management module")
        
        # Verify module was created
        module_file = project_path / "modules" / "users.py"
        assert module_file.exists()
        
        module_content = module_file.read_text()
        assert "class Users(Module)" in module_content
        assert "User management module" in module_content
        
        # Create a plugin
        create_plugin(str(project_path), "auth", "Authentication plugin")
        
        # Verify plugin was created
        plugin_file = project_path / "plugins" / "auth.py"
        assert plugin_file.exists()
        
        plugin_content = plugin_file.read_text()
        assert "class Auth(Plugin)" in plugin_content
        assert "Authentication plugin" in plugin_content
    
    def test_project_files_are_valid_python(self, temp_dir):
        """Test that generated files are valid Python."""
        project_name = "syntax_test_project"
        project_path = temp_dir / project_name
        
        # Create project
        create_project(str(project_path))
        
        # Create module and plugin
        create_module(str(project_path), "test_module", "Test module")
        create_plugin(str(project_path), "test_plugin", "Test plugin")
        
        # Test that all Python files have valid syntax
        python_files = [
            project_path / "main.py",
            project_path / "modules" / "test_module.py",
            project_path / "plugins" / "test_plugin.py",
        ]
        
        for file_path in python_files:
            assert file_path.exists()
            
            # Try to compile the file to check syntax
            with open(file_path) as f:
                source = f.read()
            
            try:
                compile(source, str(file_path), 'exec')
            except SyntaxError as e:
                pytest.fail(f"Syntax error in {file_path}: {e}")


@pytest.mark.unit
class TestCLIValidation:
    """Test CLI input validation."""
    
    def test_validate_name_valid(self):
        """Test name validation with valid names."""
        from msfw.cli import _validate_name
        
        valid_names = [
            "test",
            "test_module",
            "user_auth",
            "api_v1",
            "simple",
        ]
        
        for name in valid_names:
            # Should not raise exception
            assert _validate_name(name) is True
    
    def test_validate_name_invalid(self):
        """Test name validation with invalid names."""
        from msfw.cli import _validate_name
        
        invalid_names = [
            "123test",      # starts with number
            "test-module",  # contains hyphen
            "test module",  # contains space
            "",             # empty
        ]
        
        for name in invalid_names:
            # Invalid names should return False
            assert _validate_name(name) is False
    
    def test_project_path_validation(self, temp_dir):
        """Test project path validation."""
        # Valid path
        valid_path = temp_dir / "new_project"
        create_project(str(valid_path))
        assert valid_path.exists()
        
        # Invalid path (already exists)
        with pytest.raises(ValueError):
            create_project(str(valid_path))


@pytest.mark.unit
class TestCLIHelpers:
    """Test CLI helper functions."""
    
    def test_template_generation_with_special_characters(self):
        """Test template generation with special characters in description."""
        description = "Module with 'quotes' and \"double quotes\" and newlines\ntest"
        template = generate_module_template("TestModule", description)
        
        # Should handle special characters properly
        assert "TestModule" in template
        assert "quotes" in template
    
    def test_template_generation_empty_description(self):
        """Test template generation with empty description."""
        template = generate_module_template("TestModule", "")
        
        assert "class TestModule(Module)" in template
        # Should still generate valid template
        assert "def register_routes" in template
    
    def test_snake_case_conversion(self):
        """Test snake case conversion for names."""
        from msfw.cli import _to_snake_case
        
        test_cases = [
            ("test", "test"),
            ("testModule", "test_module"),
            ("TestModule", "test_module"),
            ("XMLParser", "xml_parser"),
            ("HTTPSConnection", "https_connection"),
        ]
        
        for input_name, expected in test_cases:
            result = _to_snake_case(input_name)
            assert result == expected, f"Expected {expected}, got {result} for input {input_name}"
    
    def test_class_name_conversion(self):
        """Test class name conversion."""
        from msfw.cli import _to_class_name
        
        test_cases = [
            ("test", "Test"),
            ("test_module", "TestModule"),
            ("user_auth", "UserAuth"),
            ("api_v1", "ApiV1"),
        ]
        
        for input_name, expected in test_cases:
            result = _to_class_name(input_name)
            assert result == expected, f"Expected {expected}, got {result} for input {input_name}"


@pytest.mark.integration
class TestCLIWithRealFiles:
    """Test CLI with real file operations."""
    
    def test_module_file_content(self, temp_dir):
        """Test that created module files have correct content."""
        project_path = temp_dir / "test_project"
        create_project(str(project_path))
        
        module_name = "user_management"
        description = "Handles user operations and authentication"
        
        create_module(str(project_path), module_name, description)
        
        module_file = project_path / "modules" / f"{module_name}.py"
        content = module_file.read_text()
        
        # Check specific content elements
        assert f'"{description}"' in content
        assert "class UserManagement(Module)" in content
        assert "def register_routes" in content
        assert "@router.get" in content
        assert "return" in content
    
    def test_plugin_file_content(self, temp_dir):
        """Test that created plugin files have correct content."""
        project_path = temp_dir / "test_project"
        create_project(str(project_path))
        
        plugin_name = "logging_plugin"
        description = "Provides enhanced logging capabilities"
        
        create_plugin(str(project_path), plugin_name, description)
        
        plugin_file = project_path / "plugins" / f"{plugin_name}.py"
        content = plugin_file.read_text()
        
        # Check specific content elements
        assert f'"{description}"' in content
        assert "class LoggingPlugin(Plugin)" in content
        assert "async def setup" in content
        assert "register_hook" in content
        assert "async def cleanup" in content
    
    def test_project_requirements_file(self, temp_dir):
        """Test that requirements.txt is created with correct content."""
        project_path = temp_dir / "test_project"
        create_project(str(project_path))
        
        requirements_file = project_path / "requirements.txt"
        assert requirements_file.exists()
        
        content = requirements_file.read_text()
        
        # Should contain MSFW and its dependencies
        expected_packages = [
            "fastapi",
            "uvicorn",
            "pydantic",
            "sqlalchemy",
            "structlog",
        ]
        
        for package in expected_packages:
            assert package in content
    
    def test_project_config_file(self, temp_dir):
        """Test that config file is created with correct structure."""
        project_path = temp_dir / "test_project"
        create_project(str(project_path))
        
        config_file = project_path / "config" / "settings.toml"
        assert config_file.exists()
        
        content = config_file.read_text()
        
        # Should contain basic configuration sections
        assert "app_name" in content
        assert "[database]" in content
        assert "[logging]" in content 