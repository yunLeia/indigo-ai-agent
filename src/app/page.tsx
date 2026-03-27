"use client";

import DemoScreen from "@/components/DemoScreen";

export default function HomePage() {
  return (
    <DemoScreen
      userName="Alex Kim"
      onLogout={() => {
        // no-op for demo
      }}
    />
  );
}
