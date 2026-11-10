"""Loading, navigating and creating B-UML objects."""

import runpy

from besser.BUML.metamodel.object import Object


def load(path):
    """Runs a B-UML .py file and returns its variables (domain_model, object_model, ...)."""
    return runpy.run_path(path)


def objects_of(model, class_name):
    # compare by name: classes loaded from a file are copies of the metamodel's
    return sorted((o for o in model.objects if o.classifier.name == class_name),
                  key=lambda o: o.name_)


def many(obj, end):
    # links are sets, so sort them to stay deterministic
    linked = {le.object for le in obj.link_ends() if le.association_end.name == end}
    return sorted(linked, key=lambda o: o.name_)


def one(obj, end):
    linked = many(obj, end)
    return linked[0] if linked else None


def attr(obj, name):
    # an optional attribute that was never set raises instead of returning None
    return getattr(obj, name, None)


def literal(value):
    # enum slots hold an EnumerationLiteral, or its name in older models
    return getattr(value, "name", value)


def new(cls, obj_name, **slots):
    obj = Object(name=obj_name, classifier=cls)
    for key, value in slots.items():
        setattr(obj, key, value)
    return obj


def enum_literal(enumeration, name):
    return next(lit for lit in enumeration.literals if lit.name == name)
