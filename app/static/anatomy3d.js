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

  // Fresnel "glass" material — bright at grazing edges, transparent face.
  // This is the glass-brain signature (edge-lit translucent shell).
  function fresnelMaterial(color, power, opacity) {
    return new T.ShaderMaterial({
      uniforms: {
        glowColor: { value: new T.Color(color) },
        power: { value: power },
        opacity: { value: opacity },
      },
      vertexShader: `
        varying vec3 vN; varying vec3 vV;
        void main() {
          vec4 mv = modelViewMatrix * vec4(position, 1.0);
          vN = normalize(normalMatrix * normal);
          vV = normalize(-mv.xyz);
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: `
        varying vec3 vN; varying vec3 vV;
        uniform vec3 glowColor; uniform float power; uniform float opacity;
        void main() {
          float f = pow(1.0 - abs(dot(normalize(vN), normalize(vV))), power);
          gl_FragColor = vec4(glowColor, clamp(f, 0.0, 1.0) * opacity);
        }`,
      transparent: true,
      blending: T.AdditiveBlending,
      side: T.DoubleSide,
      depthWrite: false,
    });
  }

  // ---- Real anatomical brain from BrainGlobe / brainrender --------------- //
  // Loads app/static/assets/brain.glb (baked by scripts/fetch_brain_mesh.py).
  // Cached across renders; falls back to the procedural glass brain if the
  // asset is missing or BrainGlobe's server was unreachable when baking.
  let brainGeoCache = null;
  function acquireBrainGeometry(done) {
    if (brainGeoCache) return done(brainGeoCache, false);
    if (!T.GLTFLoader) return done(brainGeometry(), true);
    new T.GLTFLoader().load(
      "/static/assets/brain.glb",
      (gltf) => {
        let g = null;
        gltf.scene.traverse((o) => {
          if (o.isMesh && !g) {
            o.updateWorldMatrix(true, false);
            g = o.geometry.clone();
            g.applyMatrix4(o.matrixWorld);
          }
        });
        if (!g) return done(brainGeometry(), true);
        g.center();
        g.computeVertexNormals();
        brainGeoCache = g;
        done(g, false);
      },
      undefined,
      () => done(brainGeometry(), true) // 404 / network / parse -> procedural
    );
  }

  // Builds an organ from a geometry: meshes (scaled to fit) + disposables.
  function organFromGeometry(isBrain, geo, fitTarget, ownGeo) {
    geo.computeBoundingSphere();
    const fit = fitTarget / geo.boundingSphere.radius;
    const meshes = [];
    const disposables = ownGeo ? [geo] : []; // don't dispose the cached brain geo

    if (isBrain) {
      // translucent inner shell + fresnel edge glow = "glass brain"
      const shellMat = new T.MeshPhysicalMaterial({
        color: 0x9ecbff, transparent: true, opacity: 0.12,
        roughness: 0.12, metalness: 0.0, side: T.DoubleSide,
        depthWrite: false, clearcoat: 1.0, clearcoatRoughness: 0.25,
      });
      const shell = new T.Mesh(geo, shellMat); shell.renderOrder = 0;
      const glowMat = fresnelMaterial(0x8fd0ff, 2.4, 0.95);
      const glow = new T.Mesh(geo, glowMat); glow.renderOrder = 1;
      meshes.push(shell, glow);
      disposables.push(shellMat, glowMat);
    } else {
      const mat = new T.MeshStandardMaterial({
        color: 0xd83a52, roughness: 0.42, metalness: 0.0, emissive: 0x2a0710,
      });
      meshes.push(new T.Mesh(geo, mat));
      disposables.push(mat);
    }
    meshes.forEach((m) => m.scale.setScalar(fit));
    return { meshes, disposables, fit };
  }

  // 3D anchor points for annotation markers, per organ (model space). ----- //
  const ANCHORS = {
    heart: [[-0.55, 0.2, 0.7], [0.6, 0.15, 0.5], [0.05, -0.75, 0.5], [0.35, 0.7, 0.4]],
    brain: [[-0.35, 0.5, 0.7], [0.45, 0.35, 0.6], [0.0, -0.2, 1.0], [-0.5, -0.1, 0.6]],
  };

  function labelSprite(text, accent) {
    const pad = 8, font = 22;
    const cv = document.createElement("canvas");
    const ctx = cv.getContext("2d");
    ctx.font = `600 ${font}px system-ui, sans-serif`;
    const w = ctx.measureText(text).width;
    cv.width = w + pad * 2; cv.height = font + pad * 2;
    ctx.font = `600 ${font}px system-ui, sans-serif`;
    ctx.fillStyle = "rgba(12,18,32,0.86)";
    roundRect(ctx, 0, 0, cv.width, cv.height, 8); ctx.fill();
    if (accent != null) {
      ctx.strokeStyle = "#" + accent.toString(16).padStart(6, "0");
      ctx.lineWidth = 2; roundRect(ctx, 1, 1, cv.width - 2, cv.height - 2, 8); ctx.stroke();
    }
    ctx.fillStyle = "#e8eefc";
    ctx.textBaseline = "middle";
    ctx.fillText(text, pad, cv.height / 2 + 1);
    const tex = new T.CanvasTexture(cv);
    tex.anisotropy = 4;
    const spr = new T.Sprite(new T.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
    spr.scale.set((cv.width / cv.height) * 0.12, 0.12, 1);
    spr.renderOrder = 10;
    return spr;
  }
  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }

  // Glowing marker + label for each imaging annotation, placed at organ anchors.
  function addMarkers(group, isBrain, annotations, fit) {
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
  }

  // Regions of concern: dots at explicit 3D coords, colored by severity.
  const SEV_COLOR = { high: 0xff5c7a, moderate: 0xfbbf24, low: 0x6ea8fe };
  function addRegions(group, regions, fit) {
    (regions || []).forEach((rg) => {
      if (rg.x == null) return;
      const color = SEV_COLOR[rg.severity] || SEV_COLOR.low;
      const p = new T.Vector3(rg.x, rg.y, rg.z).multiplyScalar(fit);
      const marker = new T.Mesh(
        new T.SphereGeometry(0.055, 16, 16),
        new T.MeshBasicMaterial({ color })
      );
      marker.position.copy(p);
      const halo = new T.Mesh(
        new T.SphereGeometry(0.13, 16, 16),
        new T.MeshBasicMaterial({ color, transparent: true, opacity: 0.25 })
      );
      halo.position.copy(p);
      const label = labelSprite(rg.label, color);
      label.position.copy(p).add(new T.Vector3(0.22, 0.16, 0));
      group.add(marker, halo, label);
    });
  }

  // Translucent volumetric overlay (e.g. the depression-circuit correlome
  // isosurface). Baked into the same normalized space as the brain, so it just
  // scales by `fit`. Cached; silently skipped if the asset is missing.
  const overlayCache = {};
  function addOverlay(group, overlay, fit) {
    if (!overlay || !overlay.url || !T.GLTFLoader) return;
    const build = (geo) => {
      if (!active || active.group !== group) return;
      const mat = new T.MeshStandardMaterial({
        color: overlay.color, emissive: overlay.color, emissiveIntensity: 0.55,
        transparent: true, opacity: 0.32, side: T.DoubleSide,
        depthWrite: false, roughness: 0.5, metalness: 0.0,
      });
      const mesh = new T.Mesh(geo, mat);
      mesh.scale.setScalar(fit);
      mesh.renderOrder = 2;
      group.add(mesh);
      active.disposables.push(mat);
    };
    if (overlayCache[overlay.url]) return build(overlayCache[overlay.url]);
    new T.GLTFLoader().load(
      overlay.url,
      (gltf) => {
        let g = null;
        gltf.scene.traverse((o) => {
          if (o.isMesh && !g) {
            o.updateWorldMatrix(true, false);
            g = o.geometry.clone();
            g.applyMatrix4(o.matrixWorld);
          }
        });
        if (g) { g.computeVertexNormals(); overlayCache[overlay.url] = g; build(g); }
      },
      undefined,
      () => { /* missing/failed overlay — skip silently */ }
    );
  }

  // ---- Render ------------------------------------------------------------ //
  function render(container, { focus, annotations, regions, overlay }) {
    dispose();
    const isBrain = focus === "brain";
    const width = container.clientWidth || 340;
    const height = container.clientHeight || Math.min(width, 480);

    const scene = new T.Scene();
    const camera = new T.PerspectiveCamera(42, width / height, 0.1, 100);
    camera.position.set(0, 0.2, 4.2);

    const renderer = new T.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    scene.add(new T.AmbientLight(0xffffff, isBrain ? 0.6 : 0.5));
    const key = new T.DirectionalLight(0xffffff, 0.95); key.position.set(3, 4, 5); scene.add(key);
    const rim = new T.DirectionalLight(isBrain ? 0x66ccff : 0x6ea8fe, isBrain ? 0.8 : 0.6);
    rim.position.set(-4, 1, -3); scene.add(rim);

    const group = new T.Group();
    scene.add(group);

    // Assemble the organ (brain geometry may arrive asynchronously).
    const assemble = (geo, ownGeo) => {
      if (!active || active.group !== group) {
        if (ownGeo) geo.dispose(); // a newer render superseded this one
        return;
      }
      const organ = organFromGeometry(isBrain, geo, 1.35, ownGeo);
      organ.meshes.forEach((m) => group.add(m));
      active.disposables.push(...organ.disposables);
      addMarkers(group, isBrain, annotations, organ.fit);
      if (isBrain) {
        addRegions(group, regions, organ.fit);
        addOverlay(group, overlay, organ.fit);
      }
    };

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
      const h = container.clientHeight || Math.min(w, 480);
      camera.aspect = w / h; camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    }
    window.addEventListener("resize", resize);

    active = { renderer, controls, raf, resize, scene, disposables: [], group };

    // Kick off organ assembly now that `active` exists. Brain geometry is
    // fetched asynchronously (real BrainGlobe mesh, else procedural fallback).
    if (isBrain) acquireBrainGeometry(assemble);
    else assemble(heartGeometry(), true);
  }

  function dispose() {
    if (!active) return;
    cancelAnimationFrame(active.raf);
    window.removeEventListener("resize", active.resize);
    active.controls.dispose();
    (active.disposables || []).forEach((d) => d.dispose && d.dispose());
    active.renderer.forceContextLoss?.();
    active.renderer.dispose();
    active = null;
  }

  window.Anatomy3D = { render, dispose };
})();
