# This file is the actual code for the custom Python dataset xmla_explore

# import the base class for the custom dataset
from six.moves import xrange
from dataiku.connector import Connector
import requests
import xmltodict
from xmla_common import extract_path, RecordsLimit, get_credentials
from xmla_client import XMLAClient, extract_members
from xmla_constants import XMLAConstants
from safe_logger import SafeLogger


logger = SafeLogger("xmla plugin", forbidden_keys=["password", "bearer_token"])


"""
A custom Python dataset is a subclass of Connector.

The parameters it expects and some flags to control its handling by DSS are
specified in the connector.json file.

Note: the name of the class itself is not relevant.
"""
class MyConnector(Connector):

    def __init__(self, config, plugin_config):
        """
        The configuration parameters set up by the user in the settings tab of the
        dataset are passed as a json object 'config' to the constructor.
        The static configuration parameters set up by the developer in the optional
        file settings.json at the root of the plugin directory are passed as a json
        object 'plugin_config' to the constructor
        """
        Connector.__init__(self, config, plugin_config)  # pass the parameters to the base class
        logger.info("Starting XMLA plugin v{} with config={}".format(
            XMLAConstants.PLUGIN_VERSION,
            logger.filter_secrets(config)
        ))
        self.dimensions = config.get("select_dimensions", [])
        self.measures = config.get("select_measures", [])
        self.cube = config.get("select_schema_cube")
        self.properties = config.get("select_properties", [])
        endpoint, mdx_version, username, password, bearer_token = get_credentials(config)
        self.client = XMLAClient(
            endpoint,
            version=mdx_version,
            username=username,
            password=password, 
            bearer_token=bearer_token
        )

    def get_read_schema(self):
        """
        Returns the schema that this connector generates when returning rows.

        The returned schema may be None if the schema is not known in advance.
        In that case, the dataset schema will be infered from the first rows.

        If you do provide a schema here, all columns defined in the schema
        will always be present in the output (with None value),
        even if you don't provide a value in generate_rows

        The schema must be a dict, with a single key: "columns", containing an array of
        {'name':name, 'type' : type}.

        Example:
            return {"columns" : [ {"name": "col1", "type" : "string"}, {"name" :"col2", "type" : "float"}]}

        Supported types are: string, int, bigint, float, double, date, boolean
        """

        # In this example, we don't specify a schema here, so DSS will infer the schema
        # from the columns actually returned by the generate_rows method
        return None

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                      partition_id=None, records_limit=-1):
        """
        The main reading method.

        Returns a generator over the rows of the dataset (or partition)
        Each yielded row must be a dictionary, indexed by column name.

        The dataset schema and partitioning are given for information purpose.
        """
        mdx_query = self.client.build_mdx_query(self.cube, self.dimensions, self.measures, self.properties)
        logger.info("mdx_query={}".format(mdx_query))

        cube = self.client.execute_cube(mdx_query)
        error_message = cube.get_error_message()

        if error_message:
            raise Exception("Error: {}".format(error_message))

        cells = cube.get_cells()
        horizontal_axis, vertical_axis = cube.get_axis()
        columns_names = cube.get_columns_names()
        rows_names = cube.get_rows_names()

        members = extract_path(vertical_axis[0], ["Member"])
        left_columns_names = []
        for member in members:
            left_columns_names.append(member.get("@Hierarchy", ""))
        for row in vertical_axis:
            members = extract_path(row, ["Member"])
            rows_names.append(extract_members(members))
        length_horizontal_axis = len(horizontal_axis)
        length_vertical_axis = len(vertical_axis)
        counter = 0
        limit = RecordsLimit(records_limit=records_limit)
        for row_index in xrange(0, length_vertical_axis):
            row = {}
            left_column_counter = 0
            for left_column_name in left_columns_names:
                row[left_column_name] = rows_names[row_index][left_column_counter]
                left_column_counter += 1
            for column_index in xrange(0, length_horizontal_axis):
                row["{}".format(columns_names[column_index])] = cells[counter].get("Value", {}).get("#text")
                counter +=1
            yield row
            if limit.is_reached():
                return

    def get_writer(self, dataset_schema=None, dataset_partitioning=None,
                   partition_id=None):
        """
        Returns a writer object to write in the dataset (or in a partition).

        The dataset_schema given here will match the the rows given to the writer below.

        Note: the writer is responsible for clearing the partition, if relevant.
        """
        raise NotImplementedError

    def get_partitioning(self):
        """
        Return the partitioning schema that the connector defines.
        """
        raise NotImplementedError

    def list_partitions(self, partitioning):
        """Return the list of partitions for the partitioning scheme
        passed as parameter"""
        return []

    def partition_exists(self, partitioning, partition_id):
        """Return whether the partition passed as parameter exists

        Implementation is only required if the corresponding flag is set to True
        in the connector definition
        """
        raise NotImplementedError

    def get_records_count(self, partitioning=None, partition_id=None):
        """
        Returns the count of records for the dataset (or a partition).

        Implementation is only required if the corresponding flag is set to True
        in the connector definition
        """
        raise NotImplementedError
