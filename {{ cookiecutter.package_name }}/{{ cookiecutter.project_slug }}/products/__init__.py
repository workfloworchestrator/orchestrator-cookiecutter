# Copyright {% now 'local', '%Y' %} {{ cookiecutter.author }}
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module that updates the domain models of {{ cookiecutter.project_name }}. Should contain all products.

!!! warning
    Whenever a new product is added, this should be reflected in the `ProductType` enumerator.
"""

# from {{ cookiecutter.project_slug }}.products.product_types.example_product import ExampleProduct

from orchestrator.core.domain import SUBSCRIPTION_MODEL_REGISTRY
from pydantic_forms.types import strEnum


class ProductName(strEnum):
    """An enumerator of available product names in {{ cookiecutter.project_name }}."""

    EXAMPLE_PRODUCT = "Example Product"
    """An example product."""


class ProductType(strEnum):
    """An enumerator of available product types in {{ cookiecutter.project_name }}."""

    # EXAMPLE_PRODUCT_ONE = ExampleProductOne.__name__


SUBSCRIPTION_MODEL_REGISTRY.update(
    {
        # ProductName.EXAMPLE_PRODUCT.value: ExampleProduct,
    },
)

__all__ = ["ProductName", "ProductType"]
