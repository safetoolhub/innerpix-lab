"""
Tests para utils/format_utils.py
"""
import pytest
from utils.format_utils import (
    format_size,
    format_number,
    format_file_count,
    format_percentage,
    truncate_path,
    format_count_short,
    format_size_short,
    format_count_full,
    format_size_full
)


@pytest.mark.unit
class TestFormatSize:
    """Tests para format_size()"""
    
    def test_format_bytes(self):
        assert format_size(0) == "0 B"
        assert format_size(100) == "100 B"
        assert format_size(1023) == "1023 B"
    
    def test_format_kilobytes(self):
        assert format_size(1024) == "1.0 KB"
        assert format_size(1536) == "1.5 KB"
        assert format_size(102400) == "100.0 KB"
    
    def test_format_megabytes(self):
        assert format_size(1048576) == "1.0 MB"
        assert format_size(5242880) == "5.0 MB"
    
    def test_format_gigabytes(self):
        assert format_size(1073741824) == "1.00 GB"
        assert format_size(5368709120) == "5.00 GB"
    
    def test_none_value(self):
        assert format_size(None) == "0 B"
    
    def test_negative_value(self):
        result = format_size(-1024)
        assert result.startswith("-")
        assert "KB" in result
    
    def test_invalid_value(self):
        assert format_size("invalid") == "0 B"


@pytest.mark.unit
class TestFormatNumber:
    """Tests para format_number()"""
    
    def test_small_numbers(self):
        assert format_number(0) == "0"
        assert format_number(123) == "123"
        assert format_number(999) == "999"
    
    def test_thousands(self):
        assert format_number(1000) == "1.0K"
        assert format_number(1500) == "1.5K"
        assert format_number(9999) == "10.0K"
    
    def test_large_thousands(self):
        assert format_number(10000) == "10K"
        assert format_number(50000) == "50K"
        assert format_number(999999) == "999K"
    
    def test_millions(self):
        assert format_number(1000000) == "1.0M"
        assert format_number(5500000) == "5.5M"
    
    def test_none_value(self):
        assert format_number(None) == "0"
    
    def test_negative_value(self):
        result = format_number(-1500)
        assert result.startswith("-")
        assert "K" in result


@pytest.mark.unit
class TestFormatFileCount:
    """Tests para format_file_count()"""
    
    def test_small_count(self):
        assert format_file_count(0) == "0"
        assert format_file_count(100) == "100"
    
    def test_thousands_separator(self):
        assert format_file_count(1000) == "1,000"
        assert format_file_count(1500) == "1,500"
        assert format_file_count(1000000) == "1,000,000"
    
    def test_none_value(self):
        assert format_file_count(None) == "0"
    
    def test_invalid_value(self):
        assert format_file_count("invalid") == "0"


@pytest.mark.unit
class TestFormatPercentage:
    """Tests para format_percentage()"""
    
    def test_basic_percentage(self):
        assert format_percentage(50, 100) == "50.0%"
        assert format_percentage(1, 4) == "25.0%"
        assert format_percentage(3, 4) == "75.0%"
    
    def test_zero_denominator(self):
        assert format_percentage(10, 0) == "0%"
    
    def test_complete_percentage(self):
        assert format_percentage(100, 100) == "100.0%"
    
    def test_over_hundred_percent(self):
        assert format_percentage(150, 100) == "150.0%"
    
    def test_invalid_values(self):
        assert format_percentage("invalid", 100) == "0%"
        assert format_percentage(50, "invalid") == "0%"


@pytest.mark.unit
class TestTruncatePath:
    """Tests para truncate_path()"""
    
    def test_short_path(self):
        path = "/short/path.txt"
        assert truncate_path(path, 40) == path
    
    def test_long_path(self):
        path = "/very/long/path/to/some/deep/directory/file.txt"
        result = truncate_path(path, 30)
        assert len(result) <= 30  # Can be slightly shorter due to truncation logic
        assert "..." in result
    
    def test_very_short_max_length(self):
        path = "/some/path.txt"
        result = truncate_path(path, 5)
        assert len(result) == 5
    
    def test_none_path(self):
        assert truncate_path(None) == ""
    
    def test_exact_length(self):
        path = "exactly_forty_characters_long_path.txt"
        assert truncate_path(path, 39) == path


@pytest.mark.unit
class TestFormatCountShort:
    """Tests para format_count_short()"""
    
    def test_small_numbers(self):
        assert format_count_short(0) == "0"
        assert format_count_short(500) == "500"
        assert format_count_short(999) == "999"
    
    def test_thousands(self):
        assert format_count_short(1000) == "1.0K"
        assert format_count_short(1500) == "1.5K"
        assert format_count_short(9999) == "10.0K"
    
    def test_large_thousands(self):
        assert format_count_short(10000) == "10K"
        assert format_count_short(50000) == "50K"


@pytest.mark.unit
class TestFormatSizeShort:
    """Tests para format_size_short()"""
    
    def test_bytes(self):
        assert format_size_short(0) == "0B"
        assert format_size_short(500) == "500B"
        assert format_size_short(1023) == "1023B"
    
    def test_kilobytes(self):
        assert format_size_short(1024) == "1KB"
        assert format_size_short(1536) == "2KB"  # Rounded
    
    def test_megabytes(self):
        assert format_size_short(1048576) == "1.0MB"
        assert format_size_short(5242880) == "5.0MB"
    
    def test_gigabytes(self):
        assert format_size_short(1073741824) == "1.00GB"


@pytest.mark.unit
class TestFormatCountFull:
    """Tests para format_count_full()"""
    
    def test_thousands_separator(self):
        assert format_count_full(1000) == "1,000"
        assert format_count_full(1234567) == "1,234,567"


@pytest.mark.unit
class TestFormatSizeFull:
    """Tests para format_size_full()"""
    
    def test_bytes(self):
        assert format_size_full(500) == "500 B"
    
    def test_kilobytes(self):
        assert format_size_full(1024) == "1.0 KB"
        assert format_size_full(1536) == "1.5 KB"
    
    def test_megabytes(self):
        assert format_size_full(1048576) == "1.0 MB"
    
    def test_gigabytes(self):
        assert format_size_full(1073741824) == "1.00 GB"
