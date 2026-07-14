import { useEffect, useRef } from "react";

// Renders a 2D molecular structure from a SMILES string using smiles-drawer (loaded via CDN).
export default function Structure({ smiles, width = 340, height = 300 }) {
  const canvasRef = useRef(null);
  useEffect(() => {
    if (!smiles || !canvasRef.current || !window.SmilesDrawer) return;
    const drawer = new window.SmilesDrawer.Drawer({ width, height, bondThickness: 1.1 });
    window.SmilesDrawer.parse(
      smiles,
      (tree) => drawer.draw(tree, canvasRef.current, "light", false),
      () => {
        const ctx = canvasRef.current.getContext("2d");
        ctx.clearRect(0, 0, width, height);
        ctx.fillStyle = "#888";
        ctx.font = "13px sans-serif";
        ctx.fillText("Structure unavailable for this SMILES", 12, 20);
      }
    );
  }, [smiles, width, height]);
  return <canvas ref={canvasRef} width={width} height={height} className="struct" />;
}
