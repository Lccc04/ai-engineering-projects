"""
Pandas DataFrame Core (sample)
"""
import numpy as np
from typing import Any, Dict, List, Optional, Callable


class DataFrame:
    """
    Two-dimensional, size-mutable, potentially heterogeneous tabular data.

    Primary pandas data structure with labeled axes (rows and columns).
    """

    def __init__(self, data: Dict[str, List[Any]]):
        self._data = data
        self.columns = list(data.keys())
        self.index = list(range(len(next(iter(data.values())))))
        self._validate()

    def _validate(self) -> None:
        """Ensure all columns have same length."""
        lengths = [len(v) for v in self._data.values()]
        if len(set(lengths)) > 1:
            raise ValueError("All columns must have same length")

    def head(self, n: int = 5) -> "DataFrame":
        """Return the first n rows."""
        result = {}
        for col in self.columns:
            result[col] = self._data[col][:n]
        return DataFrame(result)

    def groupby(self, by: str) -> "GroupBy":
        """
        Group DataFrame using a column key.

        Returns a GroupBy object for further aggregation.
        """
        return GroupBy(self, by)

    def fillna(self, value: Any) -> "DataFrame":
        """Fill missing values (None/NaN) with specified value."""
        result = {}
        for col in self.columns:
            result[col] = [v if v is not None else value for v in self._data[col]]
        return DataFrame(result)

    def dropna(self) -> "DataFrame":
        """Remove rows containing missing values."""
        valid_indices = set(range(len(self.index)))
        for col in self.columns:
            for i, val in enumerate(self._data[col]):
                if val is None or (isinstance(val, float) and np.isnan(val)):
                    valid_indices.discard(i)
        valid = sorted(valid_indices)
        result = {}
        for col in self.columns:
            result[col] = [self._data[col][i] for i in valid]
        return DataFrame(result)

    def merge(
        self,
        other: "DataFrame",
        on: str,
        how: str = "inner",
    ) -> "DataFrame":
        """
        Merge DataFrame with another DataFrame on a column.

        Args:
            other: Right DataFrame
            on: Column name to join on
            how: 'inner', 'left', 'right', or 'outer'
        """
        return DataFrame({})  # Simplified

    def set_index(self, keys: str) -> "DataFrame":
        """Set the DataFrame index using an existing column."""
        idx_values = self._data[keys]
        self.index = list(range(len(idx_values)))
        return self

    def loc(self, key: Any):
        """Access a group of rows by label."""
        return DataFrame({})


class GroupBy:
    """GroupBy object for split-apply-combine operations."""

    def __init__(self, df: DataFrame, by: str):
        self.df = df
        self.by = by

    def mean(self) -> DataFrame:
        """Compute mean of groups."""
        return DataFrame({})

    def sum(self) -> DataFrame:
        """Compute sum of groups."""
        return DataFrame({})

    def agg(self, func: Dict[str, str]) -> DataFrame:
        """Aggregate using specified functions per column."""
        return DataFrame({})


class Series:
    """One-dimensional ndarray with axis labels."""

    def __init__(self, data: List[Any], name: str = ""):
        self.values = data
        self.name = name

    def fillna(self, value: Any) -> "Series":
        """Fill missing values."""
        return Series([v if v is not None else value for v in self.values])

    def isna(self) -> "Series":
        """Detect missing values, returns boolean Series."""
        return Series([v is None for v in self.values])
