import json
import requests
import xmltodict
from xmla_common import get_credentials
from xmla_client import XMLAClient
from safe_logger import SafeLogger


logger = SafeLogger("xmla plugin", forbidden_keys=["password", "bearer_token"])


DEFAULT_EMPTY_CHOICE = {"label": "<Nothing>", "value": None}

def build_select_choices(choices=None):
    if not choices:
        return {"choices": []}
    if isinstance(choices, str):
        return {"choices": [{"label": "{}".format(choices)}]}
    if isinstance(choices, list):
        return {"choices": choices}
    if isinstance(choices, dict):
        returned_choices = []
        for choice_key in choices:
            returned_choices.append({
                "label": choice_key,
                "value": choices.get(choice_key)
            })
    

def do(payload, config, plugin_config, inputs):
    logger.info("do:payload={}, config={}, plugin_config={}, inputs={}".format(payload, config, plugin_config, inputs))
    parameter_name = payload.get('parameterName')
    select_catalog = config.get("select_catalog")
    select_schema_cube = config.get("select_schema_cube")
    select_dimensions = config.get("select_dimensions", [])
    
    endpoint, mdx_version, username, password, bearer_token = get_credentials(config)
    client = XMLAClient(
        endpoint,
        version=mdx_version,
        username=username,
        password=password,
        bearer_token=bearer_token
    )
    choices = Choices()

    if parameter_name == "select_catalog":
        catalogs = client.discover("DBSCHEMA_CATALOGS")
        for catalog in catalogs:
            choices.append(catalog.get("CATALOG_NAME"), catalog.get("CATALOG_NAME"))
        return choices.to_dss()

    if parameter_name == "select_schema_cube":
        if not select_catalog:
            return build_select_choices("Select a catalog")
        cubes = client.discover("MDSCHEMA_CUBES")
        for cube in cubes:
            if cube.get("CATALOG_NAME") == select_catalog:
                choices.append(cube.get("CUBE_NAME"), cube.get("CUBE_NAME"))
        return choices.to_dss()

    if parameter_name == "select_dimensions":
        if not select_catalog:
            return build_select_choices("Select a catalog")
        if not select_schema_cube:
            return build_select_choices("Select a cube")
        dimensions = client.discover("MDSCHEMA_DIMENSIONS")
        for dimension in dimensions:
            if dimension.get("CATALOG_NAME") == select_catalog and dimension.get("CUBE_NAME") == select_schema_cube:
                choices.append(dimension.get("DIMENSION_NAME"), dimension.get("DIMENSION_UNIQUE_NAME"))
        return choices.to_dss()

    if parameter_name == "select_measures":
        if not select_catalog:
            return build_select_choices("Select a catalog")
        if not select_schema_cube:
            return build_select_choices("Select a cube")
        measures = client.discover("MDSCHEMA_MEASURES")
        for measure in measures:
            if measure.get("CATALOG_NAME") == select_catalog and measure.get("CUBE_NAME") == select_schema_cube:
                choices.append(measure.get("MEASURE_NAME"), measure.get("MEASURE_UNIQUE_NAME"))
        return choices.to_dss()

    if parameter_name == "select_hierarchy":
        return build_select_choices("Ignored")
        # if not select_catalog:
        #     return build_select_choices("Select a catalog")
        # if not select_schema_cube:
        #     return build_select_choices("Select a cube")
        # hierarchies = xmla_discover("MDSCHEMA_HIERARCHIES")
        # print("ALX:hierarchies={}".format(hierarchies))
        # for hierarchy in hierarchies:
        #     choices.append(hierarchy.get("HIERARCHY_NAME"), hierarchy.get("HIERARCHY_UNIQUE_NAME"))
        # return choices.to_dss()

    if parameter_name == "select_properties":
        if not select_catalog:
            return build_select_choices("Select a catalog")
        if not select_schema_cube:
            return build_select_choices("Select a cube")
        properties = client.discover("MDSCHEMA_PROPERTIES")
        for property in properties:
            if property.get("CATALOG_NAME") == select_catalog and property.get("CUBE_NAME") == select_schema_cube and property.get("DIMENSION_UNIQUE_NAME") in select_dimensions:
                property_tag = "{}.{}".format(property.get("DIMENSION_UNIQUE_NAME"), property.get("PROPERTY_NAME"))
                choices.append(property_tag, property_tag)
        return choices.to_dss()
    return build_select_choices()


class Choices(object):
    def __init__(self):
        self.choices = []
    def append(self, label, name):
        self.choices.append(
            {
                "label": label,
                "value": name
            }
        )
    def to_dss(self):
        return build_select_choices(self.choices)
