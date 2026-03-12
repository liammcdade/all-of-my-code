from abc import ABC, abstractmethod


class DataLoader(ABC):
    """
    Abstract base class for data loaders.

    Subclasses must implement the `load_data` method to handle specific
    file types or data sources.
    """

    def __init__(self, source):
        """
        Initializes the DataLoader with the data source.

        Args:
            source (str): The path to the file or data source.
        """
        self.source = source
        if not self.source:
            raise ValueError("Data source cannot be empty.")

    @abstractmethod
    def load_data(self):
        """
        Loads data from the specified source.

        This method must be implemented by subclasses.

        Returns:
            data: The loaded data (e.g., list of lists, pandas DataFrame).

        Raises:
            NotImplementedError: If the subclass does not implement this method.
            FileNotFoundError: If the specified source file does not exist.
            Exception: For other data loading errors.
        """
        pass

    def get_source_info(self):
        """
        Returns information about the data source.

        Returns:
            str: Information about the data source.
        """
        return f"Data source: {self.source}"


# Example of how a specific loader might be structured (for illustration)
# class SpecificFileLoader(DataLoader):
# def load_data(self):
# # Check if file exists
# # import os
# # if not os.path.exists(self.source):
# # raise FileNotFoundError(f"File not found: {self.source}")
#         #
#         # try:
#         #     # Add specific loading logic here, e.g., for a CSV file
#         #     # with open(self.source, 'r') as f:
#         #     #     # Example: reading lines from a file
#         #     #     data = [line.strip().split(',') for line in f.readlines()]
#         #     # return data
#         #     print(f"Loading data from {self.source} using a specific loader...")
#         #     # Replace with actual data loading
#         #     return [["example", "data"], ["another", "row"]]
#         # except Exception as e:
#         #     raise Exception(f"Error loading data from {self.source}: {e}")


