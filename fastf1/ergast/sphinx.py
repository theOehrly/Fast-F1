import pandas as pd
from docutils import nodes
from docutils.parsers.rst import Directive, directives
import json
from typing import get_type_hints

from fastf1.ergast.interface import ErgastResultFrame
import fastf1.ergast.structure
from fastf1.version import __version__


class ApiMappingDirective(Directive):
    """A Sphinx directive to generate a description of an Ergast API endpoint
    from the object-oriented structure description in
    :mod:`fastf1.ergast.structure`.

    Required Arguments:

        - category (str): name of the category object in ``.structure`` that
          should be described

    Optional Arguments:

        - ``:subcategory: <name>``: name of the subcategory object that is
          split out from the response during flattening of the data
          (MultiResponse)

        - ``:describe-dataframe:``: flat that indicates that a description of
          the flattened data frame should be generated as well
    """
    required_arguments = 1
    option_spec = {
        'subcategory': directives.unchanged,
        'describe-dataframe': directives.flag
    }

    def _build_tree(self, category, excluded_category, *,
                    include_new_name=True):
        # Creates an object that describes the specified 'category' that
        # matches the structure of the corresponding response from ergast.
        # All values within this structure are strings that specify the data
        # type of the value in the real response and optionally also specify
        # the new name of the key after renaming (if 'include_new_name' is
        # True). If 'excluded_category' is not None, the subkey within the
        # response that matches the name of the excluded category is skipped
        # when building the object. This is used to create split
        # representations for description and content of MultiResponse objects.
        result = dict()

        for name, mapping in category['map'].items():
            # get the nicely readable name of the data type after auto casting
            _type = mapping['type']
            type_hints = get_type_hints(_type).get('return')
            if type_hints:
                # if casting is done through a conversion function like
                # `ergast.structure.time_from_ergast`, the resulting data
                # type needs to be determined from type hints
                type_str = getattr(type_hints, '__name__', str(type_hints))
            else:
                # common data types like int, float, ...: use .__name__
                type_str = _type.__name__

            if include_new_name:
                result[name] = f"{mapping['name']} <{type_str}>"
            else:
                result[name] = f"<{type_str}>"

        # recursively process subkeys
        for subcategory in category['sub']:
            if subcategory is excluded_category:
                continue

            subcontent = self._build_tree(subcategory, excluded_category,
                                          include_new_name=include_new_name)

            result[subcategory['name']] = subcontent

        # change to correct representation for keys that contain a list
        # of items
        if category['type'] is list:
            result = [result]

        return result

    def run(self):
        # get the category and splitcategory objects by name
        # splitcategory only exists for API endpoints that return
        # ErgastMultiResponse objects. It defines the subkey that is split
        # from the description df into the content df.
        root_category = getattr(fastf1.ergast.structure, self.arguments[0])
        splitcategory_name = self.options.get('subcategory')
        if splitcategory_name:
            splitcategory = getattr(fastf1.ergast.structure,
                                    splitcategory_name)
        else:
            splitcategory = None

        # First, build a full tree of the response to show the structure of
        # the original response together with the new names of keys and the
        # new data types of their values after auto casting.
        tree = self._build_tree(root_category, None)
        result_str = json.dumps(tree, indent=4).replace('"', '')

        nodes_list = \
            [nodes.raw("",
                       "<details><summary><a>API Mapping</a></summary>"
                       "Structure of the raw response, renamed key names for "
                       "flattening and dtypes for automatic type casting:"
                       "</br></br>",
                       format='html'),
             nodes.literal_block("", result_str, language='none'),
             nodes.raw("", "</details>", format='html')]

        if 'describe-dataframe' in self.options:
            # Second, add a description of how the data looks after flattening
            # in the pandas responses

            nodes_list.append(nodes.raw(
                "",
                "<details><summary><a>DataFrame Description</a></summary>"
                "DataFrame column names and dtypes for automatic type"
                "casting:</br></br>",
                format='html'
            ))

            result_str = self._generate_df_description(root_category,
                                                       splitcategory)

            if splitcategory:
                # add subheading if the response is split into a MultiResponse
                nodes_list.append(nodes.raw(
                    "",
                    "<code>ErgastMultiResponse.description</code>",
                    format='html'
                ))

            nodes_list.append(nodes.literal_block(
                "", result_str, language='none'
            ))

            if splitcategory:
                # for split responses, generate the second description of the
                # previously excluded subkey
                nodes_list.append(nodes.raw(
                    "",
                    f"<code>ErgastMultiResponse.content</code> (contains data "
                    f"from subkey <code>{splitcategory_name}</code>)",
                    format='html'
                ))

                result_str = self._generate_df_description(splitcategory, None)
                nodes_list.append(nodes.literal_block(
                    "", result_str, language='none'
                ))

            nodes_list.append(nodes.raw("", "</details>", format='html'))

        return nodes_list

    def _generate_df_description(self, root_category, splitcategory):
        # generate an object that describes the response in the same
        # structure as the response itself
        tree = self._build_tree(root_category, splitcategory,
                                include_new_name=False)
        # process this object the same way an actual response is processed, so
        # that the same renaming and transformations of the structure are
        # applied to it
        flat = ErgastResultFrame._prepare_response(tree, root_category,
                                                   cast=False)
        # print the flattened data nicely formatted as a table (use str
        # represenation of a dataframe for this)
        # remove the last line (unnecessary info about dataframe)
        result_str = '\n'.join(
            str(pd.DataFrame(flat).iloc[0]).split('\n')[:-1]
        )
        return result_str


def setup(app):
    """ Register directive with Sphinx """
    app.add_directive('ergast-api-map', ApiMappingDirective)
    return {'version': __version__}
