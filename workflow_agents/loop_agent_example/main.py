import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from prduct_loop_agent.agent import root_agent


# --- Sample Product Specs (raw catalog data) ---
SAMPLE_PRODUCTS = {
    "wireless_earbuds": """
        Brand: SonicPulse
        Product: AirBuds Pro X
        Category: True Wireless Earbuds
        Price: ₹4,999
        Driver: 12mm dynamic titanium-coated driver
        ANC: Hybrid Active Noise Cancellation up to 35dB
        Battery: 8 hours per charge, 32 hours with case
        Charging: USB-C, Qi wireless charging
        Codec: AAC, SBC, LDAC
        Water Resistance: IPX5 (sweat and rain proof)
        Connectivity: Bluetooth 5.3, multipoint (2 devices)
        Weight: 5.2g per earbud
        Colors: Midnight Black, Arctic White, Sage Green
        Warranty: 1 year standard, extendable to 2 years
        In the box: Earbuds, charging case, 3 ear tip sizes, USB-C cable, quick start guide
    """,
    "mechanical_keyboard": """
        Brand: KeyForge
        Product: K75 Wireless Mechanical Keyboard
        Category: 75% Compact Mechanical Keyboard
        Price: ₹7,499
        Switches: Hot-swappable Gateron G Pro 3.0 (Brown/Red/Blue options)
        Keycaps: Double-shot PBT, Cherry profile
        Layout: 75% (84 keys), dedicated knob for volume
        Backlight: Per-key RGB with 18 preset effects
        Connectivity: Bluetooth 5.1 (3 devices) / 2.4GHz dongle / USB-C wired
        Battery: 4000mAh, up to 200 hours without RGB
        Polling Rate: 1000Hz (wired and 2.4GHz)
        Software: KeyForge Studio for remapping and macros
        Gasket Mount: Yes, with sound-dampening foam layers
        Weight: 820g
        Warranty: 2 years
    """,
    "smart_watch": """
        Brand: PulseFit
        Product: Titan GT Sport
        Category: GPS Multisport Smartwatch
        Price: ₹12,999
        Display: 1.43" AMOLED, 466x466, 2000 nits peak brightness
        GPS: Dual-band L1+L5, multi-GNSS (GPS, GLONASS, Galileo, BeiDou)
        Health: 24/7 heart rate, SpO2, stress, skin temperature, sleep staging
        Sports Modes: 150+ including running, cycling, swimming, hiking, yoga
        Water Resistance: 5ATM + IP68 (swim-proof to 50m)
        Battery: 14 days typical use, 40 hours full GPS
        Navigation: Offline maps, breadcrumb trail, back-to-start
        Connectivity: Bluetooth 5.2, Wi-Fi, NFC for contactless payments
        Strap: 22mm quick-release, silicone included (leather/metal sold separately)
        OS: PulseFit OS 3.0 with 3rd party app support
        Weight: 52g without strap
        Warranty: 1 year
    """,
}


async def run_for_product(product_key: str):
    """Run the loop agent for a given product."""
    session_service = InMemorySessionService()

    runner = Runner(
        agent=root_agent,
        app_name="product_listing_app",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="product_listing_app",
        user_id="copywriter_1",
    )

    product_specs = SAMPLE_PRODUCTS[product_key]

    content = types.Content(
        role="user",
        parts=[types.Part(text=product_specs)],
    )

    print(f"\n{'=' * 70}")
    print(f"  PRODUCT: {product_key.replace('_', ' ').upper()}")
    print(f"{'=' * 70}")
    print(f"\n📦 Raw Specs:\n{product_specs.strip()[:250]}...\n")
    print(f"{'─' * 70}")

    iteration = 0
    async for event in runner.run_async(
        user_id="copywriter_1",
        session_id=session.id,
        new_message=content,
    ):
        if event.content and event.content.parts:
            author = event.author or "Agent"
            text = "\n".join(p.text for p in event.content.parts if p.text)
            if text.strip():
                if author == "ProductWriterAgent":
                    iteration += 1
                    label = f"✍️  DRAFT (Iteration {iteration})"
                elif author == "QAAuditorAgent":
                    label = f"🔍 QA AUDIT (Iteration {iteration})"
                else:
                    label = author

                print(f"\n{'─' * 40}")
                print(f"  {label}")
                print(f"{'─' * 40}")
                print(text.strip())

    print(f"\n{'=' * 70}")
    print(f"  LOOP COMPLETE — {iteration} iteration(s)")
    print(f"{'=' * 70}\n\n")


async def main():
    print("\nWhich product do you want to generate a listing for?\n")
    print("  1. Wireless Earbuds   (SonicPulse AirBuds Pro X)")
    print("  2. Mechanical Keyboard (KeyForge K75)")
    print("  3. Smart Watch         (PulseFit Titan GT Sport)")
    print("  4. Run ALL three\n")

    choice = input("Enter choice (1/2/3/4): ").strip()

    if choice == "1":
        await run_for_product("wireless_earbuds")
    elif choice == "2":
        await run_for_product("mechanical_keyboard")
    elif choice == "3":
        await run_for_product("smart_watch")
    elif choice == "4":
        for key in SAMPLE_PRODUCTS:
            await run_for_product(key)
    else:
        print("Invalid choice. Running wireless earbuds by default.")
        await run_for_product("wireless_earbuds")


if __name__ == "__main__":
    asyncio.run(main())