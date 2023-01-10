from docutils.parsers.rst import Directive, directives
from docutils import nodes
import json
from typing import get_type_hints, Dict, Union

import fastf1.ergast.structure
from fastf1.ergast.structure import flatten_inline_list_of_dicts
from fastf1.version import __version__


class ApiMappingDirective(Directive):
    required_arguments = 1
    option_spec = {
        'summary': directives.unchanged,
        'subcategory': directives.unchanged,
        'show-flat': directives.flag
    }

    def _create_pretty_map(self, category, splitcategory, transform) \
            -> Dict[str, str]:
        result = dict()

        for name, mapping in category['map'].items():
            _type = mapping['type']

            type_hints = get_type_hints(_type).get('return')
            if type_hints:
                type_str = getattr(type_hints, '__name__', str(type_hints))
            else:
                type_str = _type.__name__

            result[name] = f"{mapping['name']} <{type_str}>"

        for subcategory in category['sub']:
            if subcategory is splitcategory:
                continue

            subcontent = self._create_pretty_map(subcategory, splitcategory,
                                                 transform=transform)

            if (subcategory['method'] is flatten_inline_list_of_dicts
                    and transform):
                flat = {}
                flatten_inline_list_of_dicts(
                    [subcontent], subcategory, flat, cast=False, rename=False
                )
                subcontent = flat

            elif subcategory['type'] is list:
                subcontent = [subcontent]

            result[subcategory['name']] = subcontent

        return result

    def run(self):
        root_category = getattr(fastf1.ergast.structure, self.arguments[0])
        splitcategory_name = self.options.get('subcategory')
        if splitcategory_name:
            splitcategory = getattr(fastf1.ergast.structure,
                                    splitcategory_name)
        else:
            splitcategory = None

        result: Dict[str, Union[str, dict]] = \
            self._create_pretty_map(root_category, None, transform=False)
        result_str = json.dumps(result, indent=4).replace('"', '')

        summary = self.options.get('summary', "Click here")
        if 'show-flat' in self.options:
            suffix_orig = "(Original)"
            suffix_flat = "(Flattened Multi Response)"
        else:
            suffix_orig = ""
            suffix_flat = ""

        nodes_list = \
            [nodes.raw("", f"<details><summary><a>"
                           f"{summary} {suffix_orig}"
                           f"</a></summary>",
                       format='html'),
             nodes.literal_block("", result_str, language='none'),
             nodes.raw("", "</details>", format='html')]

        if 'show-flat' in self.options:
            nodes_list.append(
                nodes.raw("", f"<details><summary><a>"
                              f"{summary} {suffix_flat}"
                              f"</a></summary>",
                          format='html'),
            )

            result: Dict[str, Union[str, dict]] = \
                self._create_pretty_map(root_category, splitcategory,
                                        transform=True)
            result_str = json.dumps(result, indent=4).replace('"', '')

            if splitcategory:
                nodes_list.append(
                    nodes.raw("", "<strong>Description</strong>",
                              format='html'),
                )

            nodes_list.append(
                nodes.literal_block("", result_str, language='none'),
            )

            if splitcategory:
                nodes_list.append(
                    nodes.raw("", "<strong>Content</strong>", format='html'),
                )
                result: Dict[str, Union[str, dict]] = \
                    self._create_pretty_map(splitcategory, None,
                                            transform=True)
                result_str = json.dumps(result, indent=4).replace('"', '')

                nodes_list.append(
                    nodes.literal_block("", result_str, language='none'),
                )

            nodes_list.append(
                nodes.raw("", "</details>", format='html')
            )

        return nodes_list


def setup(app):
    """ Register directive with Sphinx """
    app.add_directive('ergast-api-map', ApiMappingDirective)
    return {'version': __version__}
