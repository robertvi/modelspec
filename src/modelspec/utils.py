import sys
import json
import bson
import yaml
import xml.etree.ElementTree as ET
import xml.dom.minidom
import os
import math
import numpy as np
import attr


from modelspec.base_types import print_
from modelspec.base_types import EvaluableExpression

from random import Random
from typing import Union

verbose = False


def load_json(filename: str):
    """
    Load a generic JSON file

    Args:
        filename: The name of the JSON file to load
    """

    with open(filename) as f:
        data = json.load(f, object_hook=ascii_encode_dict)

    return data


def load_yaml(filename: str):
    """
    Load a generic YAML file

    Args:
        filename: The name of the YAML file to load
    """
    with open(filename) as f:
        data = yaml.load(f, Loader=yaml.SafeLoader)

    return data


def load_bson(filename: str):
    """
    Load a generic BSON file

    Args:
        filename: The name of the BSON file to load
    """
    with open(filename, "rb") as infile:
        data_encoded = infile.read()
        data = bson.decode(data_encoded)

    return data


def load_xml(filename: str):
    """
    Load a generic XML file.

    Args:
        filename: The name of the XML file to load.
    """
    with open(filename, "rb") as infile:
        tree = ET.parse(infile)  # Parse the XML file into an ElementTree object
        root = tree.getroot()  # Get the root element

    # Convert the ElementTree object to a dictionary
    data = element_to_dict(root)
    removed_id = handle_id(data)
    converted_to_actual_val = convert_values(removed_id)

    return convert_values(converted_to_actual_val)


def element_to_dict(element):
    """
    This convert an ElementTree element to a dictionary.

    Args:
        element: The ElementTree element to convert.

    Returns:
        The converted dictionary.
    """
    result = {}
    attrs = element.attrib
    if attrs:
        result.update(attrs)

    children_by_tag = {}
    for child_element in element:
        child_key = child_element.tag + "s"
        child_value = element_to_dict(child_element)

        # Check if the child element has an 'id' attribute
        if "id" in child_element.attrib:
            # If the child element has an 'id', add it to the result dictionary directly
            result[child_key] = child_value
        else:
            # If the child element does not have an 'id', represent it as a list
            children_by_tag.setdefault(child_key, []).append(child_value)

    # Append the lists to the result dictionary
    result.update(children_by_tag)

    return result


def handle_id(dictionary):
    if isinstance(dictionary, dict):
        if "id" in dictionary:
            nested_dict = {dictionary["id"]: dictionary.copy()}
            del nested_dict[dictionary["id"]]["id"]
            return {k: handle_id(v) for k, v in nested_dict.items()}
        else:
            return {k: handle_id(v) for k, v in dictionary.items()}
    elif isinstance(dictionary, list):
        return [handle_id(item) for item in dictionary]
    else:
        return dictionary


def convert_values(value):
    """
    This recursively converts values to their actual types.

    Args:
        value: The value to be converted.

    Returns:
        The converted value with its actual data type.
    """
    if isinstance(value, str):
        if value.isdigit():
            return int(value)
        try:
            return float(value)
        except ValueError:
            pass
        if value.lower() == "true":
            return True
        elif value.lower() == "false":
            return False
        elif value.lower() == "none":
            return None
    elif isinstance(value, dict):
        return {key: convert_values(val) for key, val in value.items()}
    elif isinstance(value, list):
        return [convert_values(item) for item in value]

    return value


def save_to_json_file(info_dict, filename, indent=4):

    strj = json.dumps(info_dict, indent=indent)
    with open(filename, "w") as fp:
        fp.write(strj)


def save_to_yaml_file(info_dict, filename, indent=4):

    if sys.version_info[0] == 2:
        stry = yaml.dump(info_dict, indent=indent, default_flow_style=False)
    else:
        stry = yaml.dump(info_dict, indent=indent, sort_keys=False)
    with open(filename, "w") as fp:
        fp.write(stry)


def save_to_xml_file(info_dict, filename, indent=4, root="modelspec"):
    """
    This saves a dictionary to an XML file.

    Args:
        info_dict (dict): The dictionary containing the data to be saved.
        filename (str): The name of the file to save the XML data to.
        indent (int, optional): The number of spaces used for indentation in the XML file.
                                Defaults to 4.
    """

    root = build_xml_element(info_dict)

    # Generate the XML string
    xml_str = ET.tostring(root, encoding="utf-8", method="xml").decode("utf-8")

    # Create a pretty-formatted XML string using minidom
    dom = xml.dom.minidom.parseString(xml_str)
    pretty_xml_str = dom.toprettyxml(indent=" " * indent)

    # Write the XML data to the file
    with open(filename, "w", encoding="utf-8") as file:
        file.write(pretty_xml_str)


def build_xml_element(data, parent=None):
    """
    This recursively builds an XML element structure from a dictionary or a list.

    Args:
        parent: The parent XML element to attach the new element(s) to.
        data: The data to convert into XML elements.

    Returns:
        Parent
    """
    if parent is None:
        parent = ET.Element(data.__class__.__name__)

    attrs = attr.fields(data.__class__)
    for aattr in attrs:
        if isinstance(aattr.default, attr.Factory):
            children = data.__getattribute__(aattr.name)
            if not isinstance(children, (list, tuple)):
                children = [children]

            for child in children:
                child_element = build_xml_element(child)
                parent.append(child_element)
        else:
            attribute_name = aattr.name
            attribute_value = data.__getattribute__(aattr.name)
            parent.set(attribute_name, str(attribute_value))

    return parent


def ascii_encode_dict(data):
    ascii_encode = (
        lambda x: x.encode("ascii")
        if (sys.version_info[0] == 2 and isinstance(x, unicode))
        else x
    )
    return dict(map(ascii_encode, pair) for pair in data.items())


def _parse_element(dict_format, to_build):

    if verbose:
        print("Parse for element: [%s]" % dict_format)
    for k in dict_format.keys():
        if verbose:
            print(
                "  Setting id: {} in {} ({})".format(k, type.__name__, type(to_build))
            )
        to_build.id = k
        to_build = _parse_attributes(dict_format[k], to_build)

    return to_build


def _parse_attributes(dict_format, to_build):

    for key in dict_format:
        value = dict_format[key]
        new_format = True
        if verbose:
            print(
                "  Setting {}={} ({}) in {}".format(key, value, type(value), to_build)
            )

        if new_format:
            if type(to_build) == dict:
                to_build[key] = value

            elif key in to_build.allowed_children:
                type_to_use = to_build.allowed_children[key][1]
                for v in value:
                    ff = type_to_use()
                    if verbose:
                        print(f"    Type for {key}: {type_to_use} ({ff})")
                    ff = _parse_element({v: value[v]}, ff)
                    exec("to_build.%s.append(ff)" % key)
            else:
                if (
                    type(value) == str
                    or type(value) == int
                    or type(value) == float
                    or type(value) == bool
                    or type(value) == list
                    or value is None
                ):
                    to_build.__setattr__(key, value)
                else:
                    type_to_use = to_build.allowed_fields[key][1]
                    if verbose:
                        print(
                            "type_to_use: {} ({})".format(
                                type_to_use, type(type_to_use)
                            )
                        )
                        print(f"- {key} = {value}")

                    if type_to_use == EvaluableExpression:
                        vv = {}
                        to_build.__setattr__(key, vv)
                    else:
                        ff = type_to_use()
                        ff = _parse_attributes(value, ff)
                        exec("to_build.%s = ff" % key)

        else:
            if type(to_build) == dict:
                to_build[key] = value
            elif type(value) == str or type(value) == int or type(value) == float:
                to_build.__setattr__(key, value)
            elif type(value) == list:
                type_to_use = to_build.allowed_children[key][1]

                for vl in value:
                    ff = type_to_use()
                    ff = _parse_element(vl, ff)
                    exec("to_build.%s.append(ff)" % key)
            else:
                type_to_use = to_build.allowed_fields[key][1]
                ff = type_to_use()
                ff = _parse_attributes(value, ff)
                exec("to_build.%s = ff" % key)

    return to_build


def locate_file(f, base_dir):
    """
    Utility method for finding full path to a filename as string
    """
    if base_dir is None:
        return f
    file_name = os.path.join(base_dir, f)
    real = os.path.realpath(file_name)
    # print_v('- Located %s at %s'%(f,real))
    return real


def _val_info(param_val):
    if type(param_val) == np.ndarray:
        pp = "%s" % (np.array2string(param_val, threshold=4, edgeitems=1))
        pp = pp.replace("\n", "")
        pp += f" (NP {param_val.shape} {param_val.dtype})"
    elif type(param_val).__name__ == "EagerTensor":
        pp = "%s" % param_val
        pp = pp.replace("\n", "")
        # pp+=' (TF %s %s)'%(param_val.shape,param_val.dtype)
    elif type(param_val) == tuple:
        # If param_val is a tuple, recursively print its elements
        # separated by commas and wrapped in parentheses
        pp = "(" + ", ".join([_val_info(el) for el in param_val]) + ")"
    else:
        pp = "%s" % param_val
        t = type(param_val)
        if not (t == int or t == float):
            pp += "(%s)" % (t if type(t) == str else t.__name__)
    return pp


def _params_info(parameters, multiline=False):
    """
    Short info on names, values and types in parameter list
    """
    pi = "["
    if parameters is not None and len(parameters) > 0:
        for p in parameters:
            if not p == "__builtins__":
                param_val = parameters[p]
                pp = _val_info(param_val)

                pi += "{}={}, {}".format(p, pp, "\n" if multiline else "")
        pi = pi[:-2]
    pi += "]"
    return pi


# Ideas in development...
FORMAT_NUMPY = "numpy"
FORMAT_TENSORFLOW = "tensorflow"


def evaluate(
    expr: Union[int, float, str, list, dict],
    parameters: dict = {},
    rng: Random = None,
    array_format: str = FORMAT_NUMPY,
    verbose: bool = False,
    cast_to_int: bool = False,
):
    """
    Evaluate a general string like expression (e.g. "2 * weight") using a dict
    of parameters (e.g. {'weight':10}). Returns floats, ints, etc. if that's what's
    given in expr

    Args:
        expr: The expression to convert
        parameters: A dict of the parameters which can be substituted in to the expression
        rng: The random number generator to use
        array_format: numpy or tensorflow
        verbose: Print the calculations
        cast_to_int: return an int for float/string values if castable
    """

    if array_format == FORMAT_TENSORFLOW:
        import tensorflow as tf

    if verbose:
        print_(
            " > Evaluating: [%s] which is a: %s, vs parameters: %s (using %s arrays)..."
            % (expr, type(expr).__name__, _params_info(parameters), array_format),
            verbose,
        )
    try:
        if type(expr) == str and expr in parameters:
            expr = parameters[
                expr
            ]  # replace with the value in parameters & check whether it's float/int...
            if verbose:
                print_("   Using for that param: %s" % _val_info(expr), verbose)

        if type(expr) == str:
            try:
                if array_format == FORMAT_TENSORFLOW:
                    expr = tf.constant(int(expr))
                else:
                    expr = int(expr)
            except:

                try:
                    if array_format == FORMAT_TENSORFLOW:
                        expr = tf.constant(float(expr))
                    else:
                        expr = float(expr)
                except:
                    pass

        if type(expr) == list:
            if verbose:
                print_("   Returning a list in format: %s" % array_format, verbose)
            if array_format == FORMAT_TENSORFLOW:
                return tf.constant(expr, dtype=tf.float64)
            else:
                return np.array(expr)

        if type(expr) == np.ndarray:
            if verbose:
                print_(
                    "   Returning a numpy array in format: %s" % array_format, verbose
                )
            if array_format == FORMAT_TENSORFLOW:
                return tf.convert_to_tensor(expr, dtype=tf.float64)
            else:
                return np.array(expr)

        if "Tensor" in type(expr).__name__:
            if verbose:
                print_(
                    "   Returning a tensorflow Tensor in format: %s" % array_format,
                    verbose,
                )
            if array_format == FORMAT_NUMPY:
                return expr.numpy()
            else:
                return expr

        if int(expr) == expr and cast_to_int:
            if verbose:
                print_("   Returning int: %s" % int(expr), verbose)
            return int(expr)
        else:  # will have failed if not number
            if verbose:
                print_("   Returning {}: {}".format(type(expr), expr), verbose)
            return expr
    except:
        try:
            if rng:
                expr = expr.replace("random()", "rng.random()")
                parameters["rng"] = rng
            elif "random()" in expr:
                raise Exception(
                    "The expression [%s] contains a random() call, but a random number generator (rng) must be supplied to the evaluate() call when this expression string is to be evaluated"
                )

            if type(expr) == str and "math." in expr:
                parameters["math"] = math
            if type(expr) == str and "numpy." in expr:
                parameters["numpy"] = np

            if verbose:
                print_(
                    "   Trying to eval [%s] with Python using %s..."
                    % (expr, parameters.keys()),
                    verbose,
                )

            v = eval(expr, parameters)

            if verbose:
                print_(
                    "   Evaluated with Python: {} = {}".format(expr, _val_info(v)),
                    verbose,
                )

            if (type(v) == float or type(v) == str) and int(v) == v:

                if verbose:
                    print_("   Returning int: %s" % int(v), verbose)

                if array_format == FORMAT_TENSORFLOW:
                    return tf.constant(int(v))
                else:
                    return int(v)
            return v
        except Exception as e:
            if verbose:
                print_(f"   Returning without altering: {expr} (error: {e})", verbose)
            return expr


"""
    Translates a string like '3', '[0,2]' to a list
"""


def parse_list_like(list_str):

    if isinstance(list_str, int):
        return [list_str]
    elif isinstance(list_str, float):
        return [list_str]
    elif isinstance(list_str, list):
        return list_str
    elif type(list_str) == str:
        try:
            expr = int(list_str)
            return [expr]
        except:
            pass
        try:
            expr = float(list_str)
            return [expr]
        except:
            pass
        if "[" in list_str:
            return eval(list_str)
