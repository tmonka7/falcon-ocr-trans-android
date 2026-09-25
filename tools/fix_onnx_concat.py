#!/usr/bin/env python3
"""Repair rank-0 inputs to shape-building Concat nodes in paddle2onnx output.

paddle2onnx emits graphs where a ``Concat`` that assembles a shape vector mixes
rank-1 components with rank-0 scalars::

    Concat.2 axis=0 <- [Cast.2 (rank 1), Cast.4 (rank 1),
                        Cast.6 (rank 0), Cast.8 (rank 1)]

The ONNX spec requires every input to ``Concat`` to have the same rank, so ONNX
Runtime refuses to load the model at all:

    [ShapeInferenceError] All inputs to Concat must have same rank.
    Input 2 has rank 0 != 1

Paddle's own runtime is lenient about this, which is why the model works
upstream and fails here. The fix is to insert an ``Unsqueeze`` turning each
scalar into a one-element vector — exactly what the graph meant, and a no-op
numerically.

The pass is deliberately narrow: it only touches ``Concat`` nodes whose widest
input is rank 1, i.e. shape vectors. A ``Concat`` over real feature tensors is
left alone, because "promote a scalar to rank 1" would be wrong there.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import onnx
from onnx import TensorProto, helper, shape_inference

_AXES_INITIALIZER = "__concat_rank_fix_axes"


def _rank_map(model: onnx.ModelProto) -> dict[str, int]:
    """Best-effort rank for every value in the graph."""
    try:
        inferred = shape_inference.infer_shapes(model, strict_mode=False, data_prop=True)
    except Exception:
        # Partial information is still useful; an un-inferable graph simply
        # yields fewer known ranks and fewer repairs.
        inferred = model

    ranks: dict[str, int] = {}
    seq = (list(inferred.graph.value_info)
           + list(inferred.graph.input)
           + list(inferred.graph.output))
    for vi in seq:
        tensor_type = vi.type.tensor_type
        if tensor_type.HasField("shape"):
            ranks[vi.name] = len(tensor_type.shape.dim)
    for init in inferred.graph.initializer:
        ranks[init.name] = len(init.dims)
    return ranks


def _opset(model: onnx.ModelProto) -> int:
    for entry in model.opset_import:
        if entry.domain in ("", "ai.onnx"):
            return entry.version
    return 13


def repair(model: onnx.ModelProto) -> int:
    """Rewrite the graph in place. Returns how many inputs were promoted."""
    ranks = _rank_map(model)
    graph = model.graph
    opset = _opset(model)

    # Opset 13 moved Unsqueeze's axes from an attribute to a real input.
    axes_as_input = opset >= 13
    need_axes_initializer = False

    rebuilt: list[onnx.NodeProto] = []
    fixed = 0

    for node in graph.node:
        if node.op_type == "Concat":
            known = [ranks[i] for i in node.input if i in ranks]
            # Only shape vectors: every known input is a scalar or a 1-D list.
            if known and max(known) == 1:
                for index, name in enumerate(node.input):
                    if ranks.get(name) != 0:
                        continue
                    promoted = f"{name}__rank1"
                    if axes_as_input:
                        need_axes_initializer = True
                        unsqueeze = helper.make_node(
                            "Unsqueeze",
                            inputs=[name, _AXES_INITIALIZER],
                            outputs=[promoted],
                            name=f"{node.name or 'concat'}_fix_{index}",
                        )
                    else:
                        unsqueeze = helper.make_node(
                            "Unsqueeze",
                            inputs=[name],
                            outputs=[promoted],
                            axes=[0],
                            name=f"{node.name or 'concat'}_fix_{index}",
                        )
                    # Emitted before the Concat, preserving topological order.
                    rebuilt.append(unsqueeze)
                    node.input[index] = promoted
                    fixed += 1
        rebuilt.append(node)

    if fixed:
        del graph.node[:]
        graph.node.extend(rebuilt)

    existing = {init.name for init in graph.initializer}
    if need_axes_initializer and _AXES_INITIALIZER not in existing:
        graph.initializer.append(
            helper.make_tensor(_AXES_INITIALIZER, TensorProto.INT64, [1], [0]))

    return fixed


def repair_file(path: Path, verbose: bool = True) -> int:
    model = onnx.load(str(path))
    fixed = repair(model)
    if fixed:
        onnx.save(model, str(path))
    if verbose:
        print(f"    concat rank fix: promoted {fixed} scalar input(s) in {path.name}")
    return fixed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("models", nargs="+", type=Path)
    args = parser.parse_args()

    for path in args.models:
        if not path.is_file():
            sys.exit(f"no such file: {path}")
        repair_file(path)


if __name__ == "__main__":
    main()
