"""
This is the indexed_repo API
============================

FIXME: more text here

"""
from chain import Chain
from requirement import (Req, spec_as_req, filename_as_req,
                         dist_as_req, add_Reqs_to_spec)
from metadata import spec_from_dist, parse_data
from dist_naming import filename_dist, repo_dist
