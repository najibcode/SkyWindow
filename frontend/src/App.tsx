import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Satellite, ShieldAlert } from "lucide-react";
import MissionPlanner from "./components/MissionPlanner";
import HazardWatch from "./components/HazardWatch";

function App() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <header className="flex items-center justify-between px-6 py-4 border-b border-border bg-card/50 bklit-glass sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <Satellite className="w-5 h-5 text-primary" />
          <h1 className="font-sans font-semibold tracking-tight text-lg">
            SKYWINDOW <span className="text-muted-foreground font-normal">MISSION PLANNER</span>
          </h1>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono text-muted-foreground">
          <span>SYS: ONLINE</span>
          <span className="text-emerald-500">CONN: STABLE</span>
        </div>
      </header>

      <main className="flex-1 flex flex-col p-6 overflow-hidden">
        <Tabs defaultValue="hazard" className="w-full h-full flex flex-col">
          <TabsList className="grid w-full max-w-md grid-cols-2 mb-6">
            <TabsTrigger value="planner" className="flex gap-2">
              <Satellite className="w-4 h-4" />
              Mission Planner
            </TabsTrigger>
            <TabsTrigger value="hazard" className="flex gap-2">
              <ShieldAlert className="w-4 h-4" />
              Global Hazard Watch
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="planner" className="flex-1 mt-0 data-[state=active]:flex">
            <MissionPlanner />
          </TabsContent>
          
          <TabsContent value="hazard" className="flex-1 mt-0 data-[state=active]:flex">
            <HazardWatch />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}

export default App;
