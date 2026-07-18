"use strict";
/*
 * Anatomy3D — renders a rotatable 3D heart or brain with patient-specific
 * marker overlays. Uses vendored Three.js (r128) + OrbitControls.
 *
 * Public API:
 *   window.Anatomy3D.render(container, { focus, annotations })
 * Re-calling render() disposes the previous scene and mounts a new one.
 */
(function () {
  const T = window.THREE;
  let active = null; // { renderer, controls, raf, resize, scene, geo, mat }

  // ---- Organ geometries -------------------------------------------------- //
  function heartGeometry() {
    // 2D heart outline (point down, lobes up), then extrude with heavy bevel
    // to get a rounded, pillow-like 3D heart.
    const s = new T.Shape();
    const x = 0, y = 0;
    s.moveTo(x + 5, y + 5);
    s.bezierCurveTo(x + 5, y + 5, x + 4, y, x, y);
    s.bezierCurveTo(x - 6, y, x - 6, y + 7, x - 6, y + 7);
    s.bezierCurveTo(x - 6, y + 11, x - 3, y + 15.4, x + 5, y + 19);
    s.bezierCurveTo(x + 12, y + 15.4, x + 16, y + 11, x + 16, y + 7);
    s.bezierCurveTo(x + 16, y + 7, x + 16, y, x + 10, y);
    s.bezierCurveTo(x + 7, y, x + 5, y + 5, x + 5, y + 5);

    const geo = new T.ExtrudeGeometry(s, {
      depth: 4,
      bevelEnabled: true,
      bevelThickness: 5,
      bevelSize: 4,
      bevelSegments: 18,
      curveSegments: 40,
      steps: 2,
    });
    geo.center();
    geo.rotateZ(Math.PI); // point down
    geo.scale(0.09, 0.09, 0.11);
    geo.computeVertexNormals();
    return geo;
  }

  function brainGeometry() {
    const geo = new T.IcosahedronGeometry(1, 5);
    const pos = geo.attributes.position;
    const v = new T.Vector3();
    const dirs = [];
    for (let s = 0; s < 7; s++)
      dirs.push(new T.Vector3(Math.sin(s * 2.1), Math.cos(s * 1.7), Math.sin(s * 3.3)).normalize());
    for (let i = 0; i < pos.count; i++) {
      v.fromBufferAttribute(pos, i);
      const n = v.clone().normalize();
      // wrinkles: sum of sines along random directions -> gyri/sulci
      let fold = 0;
      fold += 0.06 * Math.sin(9.0 * n.dot(dirs[0]));
      fold += 0.05 * Math.sin(13.0 * n.dot(dirs[1]) + 1.3);
      fold += 0.035 * Math.sin(17.0 * n.dot(dirs[2]) + 2.1);
      fold += 0.025 * Math.sin(23.0 * n.dot(dirs[3]) + 0.7);
      let r = 1 + fold;
      // longitudinal fissure along the sagittal midline (x ~ 0), top hemisphere
      const fissure = Math.exp(-(n.x * n.x) / 0.012) * Math.max(0, n.y) * 0.16;
      r -= fissure;
      v.copy(n).multiplyScalar(r);
      v.z *= 1.18; v.y *= 0.92; // ovoid: longer front-back, a touch flatter
      pos.setXYZ(i, v.x, v.y, v.z);
    }
    geo.computeVertexNormals();
    return geo;
  }

  // 3D anchor points for annotation markers, per organ (model space). ----- //
  const ANCHORS = {
    heart: [[-0.55, 0.2, 0.7], [0.6, 0.15, 0.5], [0.05, -0.75, 0.5], [0.35, 0.7, 0.4]],
    brain: [[-0.35, 0.5, 0.7], [0.45, 0.35, 0.6], [0.0, -0.2, 1.0], [-0.5, -0.1, 0.6]],
  };

  function labelSprite(text) {
    const pad = 8, font = 22;
    const cv = document.createElement("canvas");
    const ctx = cv.getContext("2d");
    ctx.font = `600 ${font}px system-ui, sans-serif`;
    const w = ctx.measureText(text).width;
    cv.width = w + pad * 2; cv.height = font + pad * 2;
    ctx.font = `600 ${font}px system-ui, sans-serif`;
    ctx.fillStyle = "rgba(12,18,32,0.86)";
    roundRect(ctx, 0, 0, cv.width, cv.height, 8); ctx.fill();
    ctx.fillStyle = "#e8eefc";
    ctx.textBaseline = "middle";
    ctx.fillText(text, pad, cv.height / 2 + 1);
    const tex = new T.CanvasTexture(cv);
    tex.anisotropy = 4;
    const spr = new T.Sprite(new T.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
    spr.scale.set((cv.width / cv.height) * 0.34, 0.34, 1);
    spr.renderOrder = 10;
    return spr;
  }
  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }

  // ---- Render ------------------------------------------------------------ //
  function render(container, { focus, annotations }) {
    dispose();
    const isBrain = focus === "brain";
    const width = container.clientWidth || 340;
    const height = Math.min(width, 380);

    const scene = new T.Scene();
    const camera = new T.PerspectiveCamera(42, width / height, 0.1, 100);
    camera.position.set(0, 0.2, 4.2);

    const renderer = new T.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    scene.add(new T.AmbientLight(0xffffff, 0.5));
    const key = new T.DirectionalLight(0xffffff, 0.95); key.position.set(3, 4, 5); scene.add(key);
    const rim = new T.DirectionalLight(isBrain ? 0xb98cff : 0x6ea8fe, 0.6); rim.position.set(-4, 1, -3); scene.add(rim);

    const geo = isBrain ? brainGeometry() : heartGeometry();
    const mat = new T.MeshStandardMaterial({
      color: isBrain ? 0xe7b7c8 : 0xd83a52,
      roughness: isBrain ? 0.85 : 0.42,
      metalness: 0.0,
      emissive: isBrain ? 0x1a0f18 : 0x2a0710,
    });
    const mesh = new T.Mesh(geo, mat);
    geo.computeBoundingSphere();
    const fit = 1.35 / geo.boundingSphere.radius;
    mesh.scale.setScalar(fit);

    const group = new T.Group();
    group.add(mesh);

    // annotation markers + labels
    const anchors = ANCHORS[isBrain ? "brain" : "heart"];
    (annotations || []).slice(0, anchors.length).forEach((ann, i) => {
      const p = new T.Vector3(...anchors[i]).multiplyScalar(fit);
      const marker = new T.Mesh(
        new T.SphereGeometry(0.05, 16, 16),
        new T.MeshBasicMaterial({ color: 0x6ea8fe })
      );
      marker.position.copy(p);
      const halo = new T.Mesh(
        new T.SphereGeometry(0.1, 16, 16),
        new T.MeshBasicMaterial({ color: 0x6ea8fe, transparent: true, opacity: 0.22 })
      );
      halo.position.copy(p);
      const label = labelSprite(ann.label);
      label.position.copy(p).add(new T.Vector3(0.2, 0.16, 0));
      group.add(marker, halo, label);
    });
    scene.add(group);

    const controls = new T.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enablePan = false;
    controls.minDistance = 2.6;
    controls.maxDistance = 7;

    const clock = new T.Clock();
    let raf;
    function loop() {
      raf = requestAnimationFrame(loop);
      group.rotation.y += clock.getDelta() * 0.35;
      controls.update();
      renderer.render(scene, camera);
      active && (active.raf = raf);
    }
    loop();

    function resize() {
      const w = container.clientWidth || width;
      const h = Math.min(w, 380);
      camera.aspect = w / h; camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    }
    window.addEventListener("resize", resize);

    active = { renderer, controls, raf, resize, scene, geo, mat };
  }

  function dispose() {
    if (!active) return;
    cancelAnimationFrame(active.raf);
    window.removeEventListener("resize", active.resize);
    active.controls.dispose();
    active.geo.dispose();
    active.mat.dispose();
    active.renderer.forceContextLoss?.();
    active.renderer.dispose();
    active = null;
  }

  window.Anatomy3D = { render, dispose };
})();
