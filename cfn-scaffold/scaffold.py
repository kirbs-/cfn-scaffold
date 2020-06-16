import networkx as nx
import yaml
import cfnlint
import matplotlib.pyplot as plt 
import random
import pandas as pd


spec = cfnlint.helpers.load_resource(cfnlint.data.CloudSpecs)

df = pd.DataFrame.from_dict(spec['ResourceTypes']).transpose().reset_index()
df.columns = ['Resource', 'Attributes', 'Documentation', 'Properties',
       'AdditionalProperties']
df['scaffold_resource_name'] = df.Resource.apply(lambda v: v.split(":")[-1])
df['scaffold_resource_name_long'] = df.Resource.apply(lambda v: ":".join(v.split(":")[2:]))


def translate_reource_name(name):
    r = df[df.scaffold_resource_name == name]
    if r.shape[0] == 1:
        return r.Resource.values[0]
    else:
        raise CfnScaffoldException(f'"{name}" resource is not unique. Please use a more specific resource. {r.scaffold_resource_name_long.values}')
        

class CfnScaffoldException(Exception):
    pass


class Template(object):
    """[summary]

    Args:
        object ([type]): [description]
    """

    def __init__(self, **kwargs):
        """[summary]

        Args:
            config_file (string): Path to config file.
        """
        self.G = nx.MultiGraph()
        self.G.add_node('Resources')
        # self.config = yaml.safe_load(yaml_config)
        if kwargs.get('config_file'):
            with open(kwargs.get('config_file'), 'r') as f:
                self.config = yaml.safe_load(f.read())
        
    def add_resource(self, resource_name, **kwargs):
        resource = Resource(resource_name, **self.config)
        self.G.add_node(resource.alias, resource=resource)
        self.G.add_edge('Resources', resource.alias)
        return resource.alias
    
    @property
    def resources(self):
        """[summary]

        Returns:
            list: All Resource objects defined in template.
        """
        return [self.G.nodes[b]['resource'] for a, b in self.G.edges(['Resources'])]
    
    def to_yaml(self, filename):
        """[summary]

        Args:
            filename ([type]): [description]

        Returns:
            [type]: [description]
        """
        return yaml.dump(self.to_dict())
    
    def from_yaml(self, filename):
        pass
    
    def to_dict(self):
        out = {}
#         for a, b in cfn.G.edges(['Resources']):
        for resource in self.resources:
            out = {resource.alias: 
                   {"Type": resource.name, 
                    'Properties': resource.properties_dict}}
        return {"Resources": out}


class Resource(object):
    """[summary]

    Args:
        object ([type]): [description]
    """
    def __init__(self, resource_name, **kwargs):
        self.resource_name = resource_name
        self.name = translate_reource_name(resource_name)
        self.alias = kwargs.get('resource_alias', resource_name + str(random.randint(10000,99999)))
        self.properties = cfnlint.helpers.load_resource(cfnlint.data.CloudSpecs)['ResourceTypes'][self.name]['Properties']
        self.attributes = None
        self.add_tags(**kwargs)
        self.add_required_properties(**kwargs)
        
        
    def add_tags(self, **kwargs):
        if kwargs.get('tags') and self.tagable:
            self.properties['Tags']['Required'] = True
            self.properties['Tags']['Values'] = kwargs['tags']
            
    def add_required_properties(self, **kwargs):
        if kwargs.get("resources"):
            if self.resource_name in kwargs.get("resources"):
                for prop in kwargs['resources'][self.resource_name]['properties']['required']:
#                     print(prop)
                    if type(prop) == str:
                        self.properties[prop]['Required'] = True
                    if type(prop) == dict:
                        self.properties[prop]['Required'] = True
                        self.properties[prop]['Values'] = prop.values()
    
    @property
    def optional_properties(self):
        return {k:v for k, v in self.properties.items() if not v['Required']}.keys()
    
    @property
    def required_properties(self):
        return {k:v for k, v in self.properties.items() if v['Required']}.keys()
    
    @property
    def tagable(self):
        return "Tags" in self.properties.keys()
    
    @property
    def properties_dict(self):
        return {i: self.properties[i].get('Values') for i in self.required_properties}