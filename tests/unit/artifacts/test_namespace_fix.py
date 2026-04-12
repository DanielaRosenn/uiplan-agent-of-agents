"""Test namespace auto-fix functionality."""
from pathlib import Path
from uipath_claude.artifacts.materialize import fix_missing_namespaces


def test_fix_missing_ui_namespace(tmp_path):
    """Test auto-fixing missing xmlns:ui declaration."""
    xaml_file = tmp_path / "test.xaml"
    content = """<Activity mc:Ignorable="sap sap2010 sads" x:Class="Test"
  xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence>
    <ui:LogMessage Message="Hello" Level="Info" />
  </Sequence>
</Activity>"""
    xaml_file.write_text(content, encoding='utf-8')
    
    # Should fix the missing namespace
    assert fix_missing_namespaces(xaml_file) is True
    
    fixed_content = xaml_file.read_text(encoding='utf-8')
    assert 'xmlns:ui="http://schemas.uipath.com/workflow/activities"' in fixed_content
    assert 'ui:LogMessage' in fixed_content


def test_fix_missing_s_namespace(tmp_path):
    """Test auto-fixing missing xmlns:s declaration."""
    xaml_file = tmp_path / "test.xaml"
    content = """<Activity mc:Ignorable="sap sap2010 sads" x:Class="Test"
  xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence>
    <Variable x:TypeArguments="s:DateTime" Name="myDate" />
  </Sequence>
</Activity>"""
    xaml_file.write_text(content, encoding='utf-8')
    
    # Should fix the missing namespace
    assert fix_missing_namespaces(xaml_file) is True
    
    fixed_content = xaml_file.read_text(encoding='utf-8')
    assert 'xmlns:s="clr-namespace:System;assembly=System.Private.CoreLib"' in fixed_content


def test_fix_missing_scg_namespace(tmp_path):
    """Test auto-fixing missing xmlns:scg declaration."""
    xaml_file = tmp_path / "test.xaml"
    content = """<Activity mc:Ignorable="sap sap2010 sads" x:Class="Test"
  xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence>
    <Variable x:TypeArguments="scg:List(x:String)" Name="myList" />
  </Sequence>
</Activity>"""
    xaml_file.write_text(content, encoding='utf-8')
    
    # Should fix the missing namespace
    assert fix_missing_namespaces(xaml_file) is True
    
    fixed_content = xaml_file.read_text(encoding='utf-8')
    assert 'xmlns:scg="clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib"' in fixed_content


def test_no_fix_needed_when_namespace_exists(tmp_path):
    """Test that no changes are made when namespace already exists."""
    xaml_file = tmp_path / "test.xaml"
    content = """<Activity mc:Ignorable="sap sap2010 sads" x:Class="Test"
  xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
  xmlns:ui="http://schemas.uipath.com/workflow/activities">
  <Sequence>
    <ui:LogMessage Message="Hello" Level="Info" />
  </Sequence>
</Activity>"""
    xaml_file.write_text(content, encoding='utf-8')
    original_content = content
    
    # Should not make any changes
    assert fix_missing_namespaces(xaml_file) is False
    
    # Content should be unchanged
    assert xaml_file.read_text(encoding='utf-8') == original_content


def test_no_fix_needed_when_no_prefix_used(tmp_path):
    """Test that no changes are made when no ui: prefix is used."""
    xaml_file = tmp_path / "test.xaml"
    content = """<Activity mc:Ignorable="sap sap2010 sads" x:Class="Test"
  xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence>
    <WriteLine Text="Hello" />
  </Sequence>
</Activity>"""
    xaml_file.write_text(content, encoding='utf-8')
    original_content = content
    
    # Should not make any changes
    assert fix_missing_namespaces(xaml_file) is False
    
    # Content should be unchanged
    assert xaml_file.read_text(encoding='utf-8') == original_content


def test_fix_multiple_namespaces(tmp_path):
    """Test fixing multiple missing namespaces at once."""
    xaml_file = tmp_path / "test.xaml"
    content = """<Activity mc:Ignorable="sap sap2010 sads" x:Class="Test"
  xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence>
    <Variable x:TypeArguments="scg:List(x:String)" Name="myList" />
    <ui:LogMessage Message="Hello" Level="Info" />
  </Sequence>
</Activity>"""
    xaml_file.write_text(content, encoding='utf-8')
    
    # Should fix both missing namespaces
    assert fix_missing_namespaces(xaml_file) is True
    
    fixed_content = xaml_file.read_text(encoding='utf-8')
    assert 'xmlns:ui="http://schemas.uipath.com/workflow/activities"' in fixed_content
    assert 'xmlns:scg="clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib"' in fixed_content
