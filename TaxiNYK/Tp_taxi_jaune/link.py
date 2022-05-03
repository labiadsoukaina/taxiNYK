import yaml

class Link:
  def __init__(self, name, member):
      self.name = name
      self.member = member
  
  def __str__(self):
      return "I am the " + self.name 

def link_constructor(loader: yaml.SafeLoader, node: yaml.nodes.MappingNode) -> Link:
    return Link(**loader.construct_mapping(node))