import requests
import xmltodict
from xmla_common import extract_path
from safe_logger import SafeLogger
from xmla_constants import XMLAConstants
from xmla_auth import XMLAAuth
import os


logger = SafeLogger("xmla plugin", forbidden_keys=["password", "bearer_token"])


DISCOVER_REQUESTS = {
    XMLAConstants.MONDRIAN: '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n<soap-env:Envelope xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/" xmlns="urn:schemas-microsoft-com:xml-analysis"><soap-env:Body><Discover><RequestType>{}</RequestType><Restrictions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="true"/><Properties xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="true"/></Discover></soap-env:Body></soap-env:Envelope>',
    XMLAConstants.SAP_BW: '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n<soap-env:Envelope xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/" xmlns="urn:schemas-microsoft-com:xml-analysis"><soap-env:Body><Discover><RequestType>{}</RequestType><Restrictions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="true"/><Properties xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="true"/></Discover></soap-env:Body></soap-env:Envelope>',
    XMLAConstants.POWER_BI: '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n<soap-env:Envelope xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/" xmlns="urn:schemas-microsoft-com:xml-analysis"><soap-env:Body><Discover><RequestType>{}</RequestType><Restrictions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="true"/><Properties xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="true"/></Discover></soap-env:Body></soap-env:Envelope>'
}

DISCOVER_PATHS = {
    XMLAConstants.MONDRIAN: ["SOAP-ENV:Envelope", "SOAP-ENV:Body", "DiscoverResponse", "return", "root", "row"],
    XMLAConstants.SAP_BW: ["SOAP-ENV:Envelope", "SOAP-ENV:Body", "DiscoverResponse", "return", "root", "row"],
    XMLAConstants.POWER_BI: ["SOAP-ENV:Envelope", "SOAP-ENV:Body", "DiscoverResponse", "return", "root", "row"]
}

EXECUTE_REQUESTS = {
    XMLAConstants.MONDRIAN: '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n<soap-env:Envelope xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/" xmlns="urn:schemas-microsoft-com:xml-analysis"><soap-env:Body><Execute><Command><Statement>{}</Statement></Command><Properties><PropertyList><Format>Multidimensional</Format><AxisFormat>TupleFormat</AxisFormat><Catalog>FoodMart</Catalog></PropertyList></Properties></Execute></soap-env:Body></soap-env:Envelope>',
    XMLAConstants.SAP_BW: '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n<soap-env:Envelope xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/" xmlns="urn:schemas-microsoft-com:xml-analysis"><soap-env:Body><Execute><Command><Statement>{}</Statement></Command><Properties><PropertyList><Format>Multidimensional</Format><AxisFormat>TupleFormat</AxisFormat><Catalog>FoodMart</Catalog></PropertyList></Properties></Execute></soap-env:Body></soap-env:Envelope>',
    XMLAConstants.POWER_BI: '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n<soap-env:Envelope xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/" xmlns="urn:schemas-microsoft-com:xml-analysis"><soap-env:Body><Execute><Command><Statement>{}</Statement></Command><Properties><PropertyList><Format>Multidimensional</Format><AxisFormat>TupleFormat</AxisFormat><Catalog>FoodMart</Catalog></PropertyList></Properties></Execute></soap-env:Body></soap-env:Envelope>'
}


class XMLAClient(object):
    def __init__(self, endpoint, version=None, username=None, password=None, bearer_token=None):
        self.session = requests.Session()
        self.session.auth = XMLAAuth(version, username, password, bearer_token)
        self.version = version or XMLAConstants.XMLA_DEFAULT_VERSION
        self.endpoint = endpoint
        if self.version == XMLAConstants.SAP_BW:
            self.format_dimensions = self.format_sap_dimensions
        else:
            self.format_dimensions = self.format_mondrian_dimensions

    def get_headers(self):
        return {
            'SOAPAction': '"urn:schemas-microsoft-com:xml-analysis:Discover"',
            'Content-Type': 'text/xml; charset=utf-8'
        }

    def discover(self, function_name):
        data = DISCOVER_REQUESTS[self.version].format(function_name)
        json_response = self.post_xmla(data)
        rows = extract_path(json_response, DISCOVER_PATHS[self.version])
        return rows

    def execute(self, mdx_query):
        data = EXECUTE_REQUESTS[self.version].format(mdx_query)
        json_response = self.post_xmla(data)
        return json_response
    
    def execute_cube(self, mdx_query):
        data = EXECUTE_REQUESTS[self.version].format(mdx_query)
        json_response = self.post_xmla(data)
        cube = Cube(json_response, version = self.version)
        return cube

    def post_xmla(self, data):
        response = self.session.post(
            url=self.endpoint,
            data=data,
            headers=self.get_headers()
        )
        assert_response_ok(response)
        json_response = xmltodict.parse(response.content)
        return json_response

    def build_mdx_query(self, cube, dimensions, measures, properties):
        # MDX versions adaptation here
        if self.version == XMLAConstants.SAP_BW:
            mdx_query = "SELECT NON EMPTY {{{}}} ON COLUMNS, NON EMPTY {{{}}} ON ROWS {} FROM [{}]".format(
                self.format_measures(measures),
                self.format_dimensions(dimensions),
                self.format_properties(properties),
                cube
            )
        else:
            mdx_query = "SELECT NON EMPTY {{{}}} ON COLUMNS, NON EMPTY {{{}}} ON ROWS FROM [{}]".format(
                self.format_measures(measures),
                self.format_dimensions(dimensions, properties),
                cube
            )
        return mdx_query
    
    def format_measures(self, measures):
        # MDX versions adaptation here
        return "{}".format(', '.join(measures))
    
    def format_sap_dimensions(self, dimensions):
        # MDX versions adaptation here
        return "{}".format('.Children * '.join(dimensions) + '.Children')
    
    def format_mondrian_dimensions(self, dimensions, properties):
        # MDX versions adaptation here
        matched_properties = []
        for dimension in dimensions:
            match = None
            for property in properties:
                if property.startswith(dimension):
                    match = property
            matched_properties.append(match)
        formated_dimensions = []
        for dimension, matched_property in zip(dimensions, matched_properties):
            token = ""
            if matched_property:
                common = os.path.commonprefix([dimension + ".", matched_property])
                property_name = matched_property[len(common):]
                token = "{}.CurrentMember.Properties(\"{}\")".format(dimension, property_name)
            else:
                token = "{}.Children".format(dimension)
            formated_dimensions.append(token)
        return " * ".join(formated_dimensions)
    
    def format_properties(self, properties):
        # MDX versions adaptation here
        property_string = ""
        if self.version == XMLAConstants.SAP_BW and properties:
            property_string = "DIMENSION PROPERTIES {} ON ROWS".format(
                ", ".join(properties)
            )
        return property_string


class Cube(object):
    def __init__(self, json_response, version):
        self.version = XMLAConstants.XMLA_DEFAULT_VERSION or version
        self.json = json_response
        self.horizontal_axis = None
        self.vertical_axis = None

    def get_cells(self):
        return extract_path(self.json, ["SOAP-ENV:Envelope", "SOAP-ENV:Body", "ExecuteResponse", "return", "root", "CellData", "Cell"])

    def get_axis(self):
        axes = extract_path(self.json, ["SOAP-ENV:Envelope", "SOAP-ENV:Body", "ExecuteResponse", "return", "root", "Axes", "Axis"])
        horizontal_axis = extract_path(axes[XMLAConstants.HORIZONTAL_AXIS], ["Tuples", "Tuple"])
        vertical_axis = extract_path(axes[XMLAConstants.VERTICAL_AXIS], ["Tuples", "Tuple"])
        return horizontal_axis, vertical_axis

    def get_error_message(self):
        error_message = extract_path(self.json, ["SOAP-ENV:Envelope", "SOAP-ENV:Body", "SOAP-ENV:Fault", "detail", "Error", "@Description"])
        return error_message

    def assert_no_error(self):
        error_message = self.get_error_message()
        if error_message:
            raise Exception("Error: {}".format(error_message))
        
    def get_columns_names(self):
        columns_names = []
        if not self.horizontal_axis:
            self.horizontal_axis, self.vertical_axis= self.get_axis()
        members = extract_path(self.horizontal_axis[0], ["Member"])
        for column in self.horizontal_axis:
            members = extract_path(column, ["Member"])
            columns_names.append(combine_members(members))
        return columns_names
    
    def get_rows_names(self):
        rows_names = []
        if not self.vertical_axis:
            self.horizontal_axis, self.vertical_axis= self.get_axis()
        members = extract_path(self.vertical_axis[0], ["Member"])
        left_columns_names = []
        for member in members:
            left_columns_names.append(member.get("@Hierarchy", ""))
        for row in self.vertical_axis:
            members = extract_path(row, ["Member"])
            rows_names.append(extract_members(members))
        return rows_names
    
    def get_size(self):
        if not self.horizontal_axis or not self.vertical_axis:
            self.horizontal_axis, self.vertical_axis= self.get_axis()
        return len(self.horizontal_axis), len(self.vertical_axis)


def assert_response_ok(response):
    error_message = None
    if type(response)!= requests.Response:
        error_message  = "Wrong response for request"
        logger.error("{}".format(error_message))
        raise Exception(error_message)
    status_code = response.status_code
    if status_code >= 400:
        error_message = "Error {} on {}".format(status_code, response.url)
        
    if error_message:
        logger.error("{}".format(error_message))
        logger.error("Dumping content: {}".format(response.content))
        raise Exception(error_message)


def combine_members(members):
    all_members = []
    for member in members:
        all_members.append(member.get("Caption", ""))
    return "|".join(all_members)


def extract_members(members):
    all_members = []
    for member in members:
        all_members.append(member.get("Caption", ""))
    return all_members
