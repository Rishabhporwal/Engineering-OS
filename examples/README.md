# Examples — worked instantiations of the Engineering OS

The Engineering OS itself carries **no** product, business, or domain knowledge. To make the abstract
concrete, this directory holds **fully-worked instantiations** — what a completed Product Canon and a
product-specific skill set actually look like once a team has run the Foundation phase
(`engineering-os-blueprint/10-adoption-and-product-canon.md`).

These are **reference material to learn from, not part of the OS.** The OS's agents read the *active*
product's Canon from the consuming repo's `.engineering-os/knowledge-base/`, never from here.

## `brain-instantiation/`

The original instantiation the OS was first built for: **Brain**, an AI-native commerce operating
system for DTC brands (India-first; UAE/GCC sequenced). It demonstrates a complete, opinionated
binding of the OS to a real, regulated, multi-tenant, AI-heavy product.

- **`canon/`** — a fully-populated Product Canon: the BRD/TRD and `TECH/00–18` deep dives (stack,
  data architecture, metrics engine, regional adapters, intelligence layer, API contracts, mobile,
  lifecycle, cost-routing, MCP, agent roster, billing, compliance engine, the engineering operating
  model). Read this to see what each Canon slot looks like when filled in for a demanding product.
- **`product-skills/`** — skills that encode Brain's **domain** (not generic engineering): billing &
  metering (realized-GMV pricing), forecasting, the lifecycle/revenue layer, India commerce economics,
  the product Memory Layer, the Morning Brief mobile surface, and the product's AI agent design. In a
  generic OS these belong to the product, not the framework — so they live here as an example.

When adopting the OS for *your* product, you do **not** copy `brain-instantiation/`. You run the
Foundation phase and fill the templates in `canon/` for your own domain.
