import vpc
import eks
import nodegroup
import addons
import efs
import cert
import cnpg
import ubersystem
import cloudfront

# Allows site-specific modules to be loaded if present
import glob
import importlib
import os

for _site in sorted(glob.glob(os.path.join(os.path.dirname(__file__), "site_*.py"))):
    _name = os.path.basename(_site)[:-3]
    print(f"loading site module {_name}")
    importlib.import_module(_name)

import pulumi
def alias_old_project_name(args):
    """
    Automatically adds an alias to every resource to tell Pulumi 
    that it used to belong to the 'magfest-uber' project.
    """
    # Create an alias that points to the SAME resource name, 
    # but in the OLD project name.
    return pulumi.ResourceTransformationResult(
        args.props,
        pulumi.ResourceOptions(
            aliases=[pulumi.Alias(project="magfest-uber")], 
            parent=args.opts.parent if args.opts else None
        )
    )

# Register the transformation globally for this run
pulumi.runtime.register_stack_transformation(alias_old_project_name)
